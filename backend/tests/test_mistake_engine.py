"""Tests for Mistake Engine v0."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.mistakes.features import (
    build_features_for_session,
    compute_blur_count,
    compute_change_count,
    compute_mark_for_review,
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
from app.models.question_cms import Question
from app.models.session import AttemptEvent, SessionAnswer, SessionQuestion, TestSession
from app.models.syllabus import AcademicYear, Block, Theme
from app.models.user import User


# ============================================================================
# FEATURE EXTRACTION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_compute_time_spent_by_question(db: AsyncSession):
    """Test time spent calculation from QUESTION_VIEWED events."""
    # Setup: user, session
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        role="STUDENT",
    )
    db.add(user)

    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode="TUTOR",
        status="SUBMITTED",
        count=2,
        submitted_at=datetime.utcnow(),
    )
    db.add(session)

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

    db.add_all([event1, event2])
    await db.commit()

    # Compute time spent
    time_spent = await compute_time_spent_by_question(db, session.id)

    # Q1: 30 seconds (until Q2 viewed)
    # Q2: 30 seconds (until session submitted)
    assert time_spent[q1_id] == 30.0
    assert time_spent[q2_id] == 30.0


@pytest.mark.asyncio
async def test_compute_change_count(db: AsyncSession):
    """Test answer change count from ANSWER_CHANGED events."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        role="STUDENT",
    )
    db.add(user)

    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode="TUTOR",
        status="ACTIVE",
        count=2,
    )
    db.add(session)

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
        db.add(event)

    event = AttemptEvent(
        id=uuid4(),
        session_id=session.id,
        user_id=user.id,
        event_type="ANSWER_CHANGED",
        event_ts=datetime.utcnow(),
        payload_json={"question_id": str(q2_id), "from_index": 0, "to_index": 1},
    )
    db.add(event)

    await db.commit()

    # Compute change counts
    change_counts = await compute_change_count(db, session.id)

    assert change_counts[q1_id] == 2
    assert change_counts[q2_id] == 1


@pytest.mark.asyncio
async def test_compute_blur_count(db: AsyncSession):
    """Test blur count from PAUSE_BLUR events."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        role="STUDENT",
    )
    db.add(user)

    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode="TUTOR",
        status="ACTIVE",
        count=1,
    )
    db.add(session)

    q_id = uuid4()

    # 3 blur events
    for i in range(3):
        event = AttemptEvent(
            id=uuid4(),
            session_id=session.id,
            user_id=user.id,
            event_type="PAUSE_BLUR",
            event_ts=datetime.utcnow(),
            payload_json={"question_id": str(q_id), "state": "blur"},
        )
        db.add(event)

    await db.commit()

    blur_counts = await compute_blur_count(db, session.id)

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
async def test_classify_mistakes_service_integration(db: AsyncSession):
    """Test full service integration with run logging."""
    # Setup: user, year, block, theme, question
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        role="STUDENT",
    )
    db.add(user)

    year = AcademicYear(id=1, year=1, name="Year 1")
    db.add(year)

    block = Block(id=uuid4(), year=1, name="Block 1", order=1)
    db.add(block)

    theme = Theme(
        id=uuid4(),
        year=1,
        block_id=block.id,
        name="Theme 1",
        order=1,
    )
    db.add(theme)

    question = Question(
        id=uuid4(),
        year=1,
        block_id=block.id,
        theme_id=theme.id,
        stem_text="Q1",
        status="PUBLISHED",
    )
    db.add(question)

    # Create session
    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode="TUTOR",
        status="SUBMITTED",
        count=1,
        submitted_at=datetime.utcnow(),
    )
    db.add(session)

    # Create session question
    sq = SessionQuestion(
        id=uuid4(),
        session_id=session.id,
        question_id=question.id,
        order_index=0,
    )
    db.add(sq)

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
    db.add(answer)

    await db.commit()

    # Call service
    result = await classify_mistakes_v0_for_session(db, session.id, trigger="test")

    # Verify result
    assert result["total_wrong"] == 1
    assert result["classified"] == 1
    assert "run_id" in result

    # Check mistake_log created
    stmt = select(MistakeLog).where(
        MistakeLog.session_id == session.id,
        MistakeLog.question_id == question.id,
    )
    log_result = await db.execute(stmt)
    mistake = log_result.scalar_one_or_none()

    assert mistake is not None
    assert mistake.mistake_type == MISTAKE_TYPE_KNOWLEDGE_GAP  # No telemetry → fallback
    assert mistake.is_correct == False

    # Check algo_run logged
    run_id = result["run_id"]
    run = await db.get(AlgoRun, run_id)
    assert run is not None
    assert run.status == "SUCCESS"


@pytest.mark.asyncio
async def test_upsert_idempotency(db: AsyncSession):
    """Test that re-running classification updates existing records."""
    # Setup minimal data
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        role="STUDENT",
    )
    db.add(user)

    question = Question(
        id=uuid4(),
        year=1,
        block_id=uuid4(),
        theme_id=uuid4(),
        stem_text="Q1",
        status="PUBLISHED",
    )
    db.add(question)

    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode="TUTOR",
        status="SUBMITTED",
        count=1,
        submitted_at=datetime.utcnow(),
    )
    db.add(session)

    sq = SessionQuestion(
        id=uuid4(),
        session_id=session.id,
        question_id=question.id,
        order_index=0,
    )
    db.add(sq)

    answer = SessionAnswer(
        id=uuid4(),
        session_id=session.id,
        user_id=user.id,
        question_id=question.id,
        selected_index=1,
        is_correct=False,
        changed_count=0,
    )
    db.add(answer)

    await db.commit()

    # Run classification twice
    result1 = await classify_mistakes_v0_for_session(db, session.id, trigger="test1")
    result2 = await classify_mistakes_v0_for_session(db, session.id, trigger="test2")

    # Both succeed
    assert result1["classified"] == 1
    assert result2["classified"] == 1

    # Check only one mistake_log row exists
    stmt = select(MistakeLog).where(MistakeLog.session_id == session.id)
    log_result = await db.execute(stmt)
    mistakes = log_result.scalars().all()

    assert len(mistakes) == 1  # Not duplicated


@pytest.mark.asyncio
async def test_best_effort_on_failure(db: AsyncSession):
    """Test that classification failures return error dict, not exception."""
    # Try to classify a non-existent session
    result = await classify_mistakes_v0_for_session(
        db, session_id=uuid4(), trigger="test"  # Doesn't exist
    )

    # Should return error dict, not raise
    assert "error" in result
    assert result["classified"] == 0
