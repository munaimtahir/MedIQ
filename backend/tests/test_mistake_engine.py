"""Tests for Mistake Engine v0."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.mistakes.features import (
    compute_blur_count,
    compute_change_count,
    compute_time_spent_by_question,
)
from app.learning_engine.mistakes.service import classify_mistakes_v0_for_session
from app.learning_engine.mistakes.v0 import (
    MISTAKE_TYPE_CHANGED_ANSWER_WRONG,
    MISTAKE_TYPE_DISTRACTED_WRONG,
    MISTAKE_TYPE_FAST_WRONG,
    MISTAKE_TYPE_KNOWLEDGE_GAP,
    MISTAKE_TYPE_SLOW_WRONG,
    MISTAKE_TYPE_TIME_PRESSURE_WRONG,
    classify_mistake_v0,
)
from app.models.learning import AlgoRun
from app.models.mistakes import MistakeLog
from app.models.question_cms import Question, QuestionStatus
from app.models.session import AttemptEvent, SessionAnswer, SessionQuestion, SessionMode, SessionStatus, TestSession
from app.models.syllabus import Year, Block, Theme
from app.core.security import hash_password
from app.models.user import User, UserRole

# ============================================================================
# FEATURE EXTRACTION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_compute_time_spent_by_question(db_session: AsyncSession):
    """Test time spent calculation from QUESTION_VIEWED events."""
    # Setup: user, session
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)

    from app.models.session import SessionMode, SessionStatus
    
    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.SUBMITTED,
        year=1,
        blocks_json=["A"],
        total_questions=2,
        started_at=datetime.utcnow(),
        submitted_at=datetime.utcnow(),
    )
    db_session.add(session)

    q1_id = uuid4()
    q2_id = uuid4()

    # Create QUESTION_VIEWED events
    # Q1 viewed at T+0, Q2 viewed at T+30, session submitted at T+60
    base_time = datetime.utcnow() - timedelta(seconds=60)

    event1 = AttemptEvent(
        id=uuid4(),
        session_id=session.id,
        user_id=user.id,
        event_type="QUESTION_VIEWED",
        event_ts=base_time,
        payload_json={"question_id": str(q1_id)},
    )

    event2 = AttemptEvent(
        id=uuid4(),
        session_id=session.id,
        user_id=user.id,
        event_type="QUESTION_VIEWED",
        event_ts=base_time + timedelta(seconds=30),
        payload_json={"question_id": str(q2_id)},
    )

    db_session.add_all([event1, event2])
    await db_session.commit()

    # Compute time spent
    time_spent = await compute_time_spent_by_question(db_session, session.id)

    # Q1: 30 seconds (until Q2 viewed)
    # Q2: 30 seconds (until session submitted)
    assert time_spent[q1_id] == 30.0
    assert time_spent[q2_id] == 30.0


@pytest.mark.asyncio
async def test_compute_change_count(db_session: AsyncSession):
    """Test answer change count from ANSWER_CHANGED events."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)

    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.ACTIVE,
        year=1,
        blocks_json=["A"],
        total_questions=2,
    )
    db_session.add(session)

    q1_id = uuid4()
    q2_id = uuid4()

    # Q1: 2 changes, Q2: 1 change
    for i in range(2):
        event = AttemptEvent(
            id=uuid4(),
            session_id=session.id,
            user_id=user.id,
            event_type="ANSWER_CHANGED",
            event_ts=datetime.utcnow(),
            payload_json={"question_id": str(q1_id), "from_index": i, "to_index": i + 1},
        )
        db_session.add(event)

    event = AttemptEvent(
        id=uuid4(),
        session_id=session.id,
        user_id=user.id,
        event_type="ANSWER_CHANGED",
        event_ts=datetime.utcnow(),
        payload_json={"question_id": str(q2_id), "from_index": 0, "to_index": 1},
    )
    db_session.add(event)

    await db_session.commit()

    # Compute change counts
    change_counts = await compute_change_count(db_session, session.id)

    assert change_counts[q1_id] == 2
    assert change_counts[q2_id] == 1


@pytest.mark.asyncio
async def test_compute_blur_count(db_session: AsyncSession):
    """Test blur count from PAUSE_BLUR events."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)

    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.ACTIVE,
        year=1,
        blocks_json=["A"],
        total_questions=1,
    )
    db_session.add(session)

    q_id = uuid4()

    # 3 blur events
    for _i in range(3):
        event = AttemptEvent(
            id=uuid4(),
            session_id=session.id,
            user_id=user.id,
            event_type="PAUSE_BLUR",
            event_ts=datetime.utcnow(),
            payload_json={"question_id": str(q_id), "state": "blur"},
        )
        db_session.add(event)

    await db_session.commit()

    blur_counts = await compute_blur_count(db_session, session.id)

    assert blur_counts[q_id] == 3


# ============================================================================
# CLASSIFICATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_classify_changed_answer_wrong():
    """Test CHANGED_ANSWER_WRONG classification (precedence #1)."""
    from app.learning_engine.mistakes.features import AttemptFeatures

    features = AttemptFeatures(
        question_id=uuid4(),
        position=0,
        is_correct=False,
        answered_at=datetime.utcnow(),
        time_spent_sec=15.0,  # Would trigger FAST_WRONG if not for change
        change_count=2,
        blur_count=0,
        mark_for_review_used=False,
        remaining_sec_at_answer=100.0,
        year=1,
        block_id=None,
        theme_id=None,
    )

    params = {
        "fast_wrong_sec": 20,
        "slow_wrong_sec": 90,
        "time_pressure_remaining_sec": 60,
        "blur_threshold": 1,
        "severity_rules": {
            "CHANGED_ANSWER_WRONG": 2,
            "FAST_WRONG": 1,
        },
    }

    classification = classify_mistake_v0(features, params)

    assert classification is not None
    assert classification.mistake_type == MISTAKE_TYPE_CHANGED_ANSWER_WRONG
    assert classification.severity == 2
    assert classification.evidence["change_count"] == 2
    assert classification.evidence["rule_fired"] == MISTAKE_TYPE_CHANGED_ANSWER_WRONG


@pytest.mark.asyncio
async def test_classify_time_pressure_wrong():
    """Test TIME_PRESSURE_WRONG classification (precedence #2)."""
    from app.learning_engine.mistakes.features import AttemptFeatures

    features = AttemptFeatures(
        question_id=uuid4(),
        position=0,
        is_correct=False,
        answered_at=datetime.utcnow(),
        time_spent_sec=50.0,
        change_count=0,
        blur_count=0,
        mark_for_review_used=False,
        remaining_sec_at_answer=30.0,  # Under time pressure
        year=1,
        block_id=None,
        theme_id=None,
    )

    params = {
        "fast_wrong_sec": 20,
        "slow_wrong_sec": 90,
        "time_pressure_remaining_sec": 60,
        "blur_threshold": 1,
        "severity_rules": {
            "TIME_PRESSURE_WRONG": 2,
        },
    }

    classification = classify_mistake_v0(features, params)

    assert classification.mistake_type == MISTAKE_TYPE_TIME_PRESSURE_WRONG
    assert classification.evidence["remaining_sec_at_answer"] == 30.0


@pytest.mark.asyncio
async def test_classify_fast_wrong():
    """Test FAST_WRONG classification (precedence #3)."""
    from app.learning_engine.mistakes.features import AttemptFeatures

    features = AttemptFeatures(
        question_id=uuid4(),
        position=0,
        is_correct=False,
        answered_at=datetime.utcnow(),
        time_spent_sec=15.0,  # Fast
        change_count=0,
        blur_count=0,
        mark_for_review_used=False,
        remaining_sec_at_answer=200.0,
        year=1,
        block_id=None,
        theme_id=None,
    )

    params = {
        "fast_wrong_sec": 20,
        "slow_wrong_sec": 90,
        "time_pressure_remaining_sec": 60,
        "blur_threshold": 1,
        "severity_rules": {
            "FAST_WRONG": 1,
        },
    }

    classification = classify_mistake_v0(features, params)

    assert classification.mistake_type == MISTAKE_TYPE_FAST_WRONG
    assert classification.severity == 1
    assert classification.evidence["time_spent_sec"] == 15.0


@pytest.mark.asyncio
async def test_classify_distracted_wrong():
    """Test DISTRACTED_WRONG classification (precedence #4)."""
    from app.learning_engine.mistakes.features import AttemptFeatures

    features = AttemptFeatures(
        question_id=uuid4(),
        position=0,
        is_correct=False,
        answered_at=datetime.utcnow(),
        time_spent_sec=50.0,
        change_count=0,
        blur_count=2,  # Distracted
        mark_for_review_used=False,
        remaining_sec_at_answer=200.0,
        year=1,
        block_id=None,
        theme_id=None,
    )

    params = {
        "fast_wrong_sec": 20,
        "slow_wrong_sec": 90,
        "time_pressure_remaining_sec": 60,
        "blur_threshold": 1,
        "severity_rules": {
            "DISTRACTED_WRONG": 1,
        },
    }

    classification = classify_mistake_v0(features, params)

    assert classification.mistake_type == MISTAKE_TYPE_DISTRACTED_WRONG
    assert classification.evidence["blur_count"] == 2


@pytest.mark.asyncio
async def test_classify_slow_wrong():
    """Test SLOW_WRONG classification (precedence #5)."""
    from app.learning_engine.mistakes.features import AttemptFeatures

    features = AttemptFeatures(
        question_id=uuid4(),
        position=0,
        is_correct=False,
        answered_at=datetime.utcnow(),
        time_spent_sec=120.0,  # Slow
        change_count=0,
        blur_count=0,
        mark_for_review_used=False,
        remaining_sec_at_answer=200.0,
        year=1,
        block_id=None,
        theme_id=None,
    )

    params = {
        "fast_wrong_sec": 20,
        "slow_wrong_sec": 90,
        "time_pressure_remaining_sec": 60,
        "blur_threshold": 1,
        "severity_rules": {
            "SLOW_WRONG": 2,
        },
    }

    classification = classify_mistake_v0(features, params)

    assert classification.mistake_type == MISTAKE_TYPE_SLOW_WRONG
    assert classification.evidence["time_spent_sec"] == 120.0


@pytest.mark.asyncio
async def test_classify_knowledge_gap_fallback():
    """Test KNOWLEDGE_GAP as fallback (precedence #6)."""
    from app.learning_engine.mistakes.features import AttemptFeatures

    features = AttemptFeatures(
        question_id=uuid4(),
        position=0,
        is_correct=False,
        answered_at=datetime.utcnow(),
        time_spent_sec=50.0,  # Not fast, not slow
        change_count=0,
        blur_count=0,
        mark_for_review_used=False,
        remaining_sec_at_answer=200.0,
        year=1,
        block_id=None,
        theme_id=None,
    )

    params = {
        "fast_wrong_sec": 20,
        "slow_wrong_sec": 90,
        "time_pressure_remaining_sec": 60,
        "blur_threshold": 1,
        "severity_rules": {
            "KNOWLEDGE_GAP": 2,
        },
    }

    classification = classify_mistake_v0(features, params)

    assert classification.mistake_type == MISTAKE_TYPE_KNOWLEDGE_GAP


@pytest.mark.asyncio
async def test_classify_missing_telemetry():
    """Test fallback to KNOWLEDGE_GAP when telemetry missing."""
    from app.learning_engine.mistakes.features import AttemptFeatures

    features = AttemptFeatures(
        question_id=uuid4(),
        position=0,
        is_correct=False,
        answered_at=datetime.utcnow(),
        time_spent_sec=None,  # Missing
        change_count=0,
        blur_count=0,
        mark_for_review_used=False,
        remaining_sec_at_answer=None,  # Missing
        year=1,
        block_id=None,
        theme_id=None,
    )

    params = {
        "fast_wrong_sec": 20,
        "slow_wrong_sec": 90,
        "time_pressure_remaining_sec": 60,
        "blur_threshold": 1,
        "severity_rules": {
            "KNOWLEDGE_GAP": 2,
        },
    }

    classification = classify_mistake_v0(features, params)

    # Should still classify (fallback to KNOWLEDGE_GAP)
    assert classification.mistake_type == MISTAKE_TYPE_KNOWLEDGE_GAP
    assert classification.evidence["time_spent_sec"] is None


@pytest.mark.asyncio
async def test_classify_correct_answer_returns_none():
    """Test that correct answers are not classified."""
    from app.learning_engine.mistakes.features import AttemptFeatures

    features = AttemptFeatures(
        question_id=uuid4(),
        position=0,
        is_correct=True,  # Correct
        answered_at=datetime.utcnow(),
        time_spent_sec=15.0,
        change_count=2,
        blur_count=3,
        mark_for_review_used=True,
        remaining_sec_at_answer=30.0,
        year=1,
        block_id=None,
        theme_id=None,
    )

    params = {
        "fast_wrong_sec": 20,
        "slow_wrong_sec": 90,
        "time_pressure_remaining_sec": 60,
        "blur_threshold": 1,
        "severity_rules": {},
    }

    classification = classify_mistake_v0(features, params)

    # Correct answers return None
    assert classification is None


# ============================================================================
# SERVICE + UPSERT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_classify_mistakes_service_integration(db_session: AsyncSession):
    """Test full service integration with run logging."""
    # Setup: user, year, block, theme, question
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)

    year = Year(id=1, name="1st Year", order_no=1, is_active=True)
    db_session.add(year)

    block = Block(id=1, year_id=1, code="A", name="Block 1", order_no=1, is_active=True)
    db_session.add(block)
    await db_session.flush()

    theme = Theme(
        id=1,
        block_id=block.id,
        title="Theme 1",
        order_no=1,
        is_active=True,
    )
    db_session.add(theme)
    
    question = Question(
        id=uuid4(),
        year_id=1,
        block_id=block.id,
        theme_id=theme.id,
        stem="Q1",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        option_e="E",
        correct_index=0,
        status=QuestionStatus.PUBLISHED,
        cognitive_level="UNDERSTAND",
        difficulty="MEDIUM",
    )
    db_session.add(question)

    # Create session
    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.SUBMITTED,
        year=1,
        blocks_json=["A"],
        total_questions=1,
        submitted_at=datetime.utcnow(),
    )
    db_session.add(session)

    # Create session question
    sq = SessionQuestion(
        id=uuid4(),
        session_id=session.id,
        question_id=question.id,
        position=0,
    )
    db_session.add(sq)

    # Create wrong answer
    answer = SessionAnswer(
        id=uuid4(),
        session_id=session.id,
        user_id=user.id,
        question_id=question.id,
        selected_index=1,
        is_correct=False,  # Wrong
        changed_count=2,  # Changed answer
    )
    db_session.add(answer)

    await db_session.commit()

    # Call service
    result = await classify_mistakes_v0_for_session(db_session, session.id, trigger="test")

    # Verify result
    assert result["total_wrong"] == 1
    assert result["classified"] == 1
    assert "run_id" in result

    # Check mistake_log created
    stmt = select(MistakeLog).where(
        MistakeLog.session_id == session.id,
        MistakeLog.question_id == question.id,
    )
    log_result = await db_session.execute(stmt)
    mistake = log_result.scalar_one_or_none()

    assert mistake is not None
    assert mistake.mistake_type == MISTAKE_TYPE_KNOWLEDGE_GAP  # No telemetry → fallback
    assert not mistake.is_correct

    # Check algo_run logged
    run_id = result["run_id"]
    run_result = await db_session.execute(select(AlgoRun).where(AlgoRun.id == run_id))
    run = run_result.scalar_one_or_none()
    assert run is not None
    assert run.status == "SUCCESS"


@pytest.mark.asyncio
async def test_upsert_idempotency(db_session: AsyncSession):
    """Test that re-running classification updates existing records."""
    # Setup minimal data
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)

    # Create year, block, theme first
    year = Year(id=1, name="1st Year", order_no=1, is_active=True)
    db_session.add(year)
    block = Block(id=1, year_id=1, code="A", name="Test Block", order_no=1, is_active=True)
    db_session.add(block)
    theme = Theme(id=1, block_id=1, title="Test Theme", order_no=1, is_active=True)
    db_session.add(theme)
    await db_session.flush()
    
    question = Question(
        id=uuid4(),
        year_id=1,
        block_id=1,
        theme_id=1,
        stem="Q1",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        option_e="E",
        correct_index=0,
        status=QuestionStatus.PUBLISHED,
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(question)

    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.SUBMITTED,
        year=1,
        blocks_json=["A"],
        total_questions=1,
        submitted_at=datetime.utcnow(),
    )
    db_session.add(session)

    sq = SessionQuestion(
        id=uuid4(),
        session_id=session.id,
        question_id=question.id,
        position=0,
    )
    db_session.add(sq)

    answer = SessionAnswer(
        id=uuid4(),
        session_id=session.id,
        user_id=user.id,
        question_id=question.id,
        selected_index=1,
        is_correct=False,
        changed_count=0,
    )
    db_session.add(answer)

    await db_session.commit()

    # Run classification twice
    result1 = await classify_mistakes_v0_for_session(db_session, session.id, trigger="test1")
    result2 = await classify_mistakes_v0_for_session(db_session, session.id, trigger="test2")

    # Both succeed
    assert result1["classified"] == 1
    assert result2["classified"] == 1

    # Check only one mistake_log row exists
    stmt = select(MistakeLog).where(MistakeLog.session_id == session.id)
    log_result = await db_session.execute(stmt)
    mistakes = log_result.scalars().all()

    assert len(mistakes) == 1  # Not duplicated


@pytest.mark.asyncio
async def test_best_effort_on_failure(db_session: AsyncSession):
    """Test that classification failures return error dict, not exception."""
    # Try to classify a non-existent session
    result = await classify_mistakes_v0_for_session(
        db_session, session_id=uuid4(), trigger="test"  # Doesn't exist
    )

    # Should return error dict, not raise
    assert "error" in result
    assert result["classified"] == 0
