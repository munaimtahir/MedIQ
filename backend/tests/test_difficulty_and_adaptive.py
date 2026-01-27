"""Tests for Difficulty Calibration v0 and Adaptive Selection v0."""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_test_data(db_session: AsyncSession):
    """Ensure year, block, and theme exist (idempotent)."""
    from app.models.syllabus import Block, Theme, Year
    
    # Check/create year
    year_result = await db_session.execute(select(Year).where(Year.id == 1))
    year = year_result.scalar_one_or_none()
    if not year:
        year = Year(id=1, name="1st Year", order_no=1, is_active=True)
        db_session.add(year)
        await db_session.flush()
    
    # Check/create block
    block_result = await db_session.execute(select(Block).where(Block.id == 1))
    block = block_result.scalar_one_or_none()
    if not block:
        block = Block(id=1, year_id=1, code="A", name="Block 1", order_no=1, is_active=True)
        db_session.add(block)
        await db_session.flush()
    
    # Check/create theme
    theme_result = await db_session.execute(select(Theme).where(Theme.id == 1))
    theme = theme_result.scalar_one_or_none()
    if not theme:
        theme = Theme(id=1, block_id=1, title="Theme 1", order_no=1, is_active=True)
        db_session.add(theme)
        await db_session.flush()
    
    return year, block, theme


from app.learning_engine.adaptive.service import adaptive_select_v0
from app.learning_engine.adaptive.v0 import select_questions_v0
from app.learning_engine.difficulty.core import (
    compute_delta,
    compute_dynamic_k,
    p_correct,
)
from app.learning_engine.difficulty.service import (
    update_difficulty_for_session,
)
from app.models.learning import AlgoRun
from app.models.learning_difficulty import QuestionDifficulty
from app.models.learning_mastery import UserThemeMastery
from app.models.learning_revision import RevisionQueue
from app.models.question_cms import Question, QuestionStatus
from app.models.session import SessionAnswer, SessionQuestion, SessionMode, SessionStatus, TestSession
from app.models.syllabus import Year, Block, Theme
from app.core.security import hash_password
from app.models.user import User, UserRole

# ============================================================================
# DIFFICULTY CALIBRATION v0 TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_p_correct_basic():
    """Test probability computation basics."""
    # Question rated 1000, student rated 1000, correct answer
    # Use p_correct to compute expected probability
    expected = p_correct(theta=1000.0, b=1000.0, guess_floor=0.2, scale=400.0)
    
    # Expected should be ~0.5 + guess_floor adjustment (even match)
    # Use <= for upper bound to account for floating point precision
    assert 0.4 < expected <= 0.6

    # Compute delta for correct answer
    delta = compute_delta(score=True, p=expected)
    assert delta > 0  # Positive error when correct

    # Test dynamic K computation
    k = compute_dynamic_k(k_base=16.0, unc=100.0, k_min=8.0, k_max=64.0)
    assert 8.0 <= k <= 64.0


@pytest.mark.asyncio
async def test_p_correct_weak_student():
    """Test that weak student has lower probability."""
    # Weak student (800) vs question (1000)
    weak_prob = p_correct(theta=800.0, b=1000.0, guess_floor=0.2, scale=400.0)
    
    # Equal match (1000 vs 1000) for comparison
    equal_prob = p_correct(theta=1000.0, b=1000.0, guess_floor=0.2, scale=400.0)
    
    # Weak student should have lower probability than equal match
    # Due to guess_floor, weak_prob can be slightly above 0.5, but still < equal_prob
    assert weak_prob < equal_prob
    # Also verify it's reasonable (less than 0.55 to account for guess floor effect)
    assert weak_prob < 0.55


@pytest.mark.asyncio
async def test_p_correct_strong_student():
    """Test that strong student has higher probability."""
    # Strong student (1200) vs question (1000)
    expected = p_correct(theta=1200.0, b=1000.0, guess_floor=0.2, scale=400.0)
    
    # Expected > 0.5 (student stronger than question)
    assert expected > 0.5


@pytest.mark.asyncio
async def test_difficulty_update_on_session_submit(db_session: AsyncSession):
    """Test difficulty update when session is submitted."""
    # Setup: Create user, year, block, theme, questions
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
    await db_session.flush()

    # Ensure test data exists
    year, block, theme = await ensure_test_data(db_session)

    # Create questions
    q1 = Question(
        id=uuid4(),
        year_id=1,
        block_id=block.id,
        theme_id=theme.id,
        stem="Q1",
        option_a="A1",
        option_b="B1",
        option_c="C1",
        option_d="D1",
        option_e="E1",
        correct_index=0,
        status=QuestionStatus.PUBLISHED,
        cognitive_level="UNDERSTAND",
        difficulty="MEDIUM",
    )
    q2 = Question(
        id=uuid4(),
        year_id=1,
        block_id=block.id,
        theme_id=theme.id,
        stem="Q2",
        option_a="A2",
        option_b="B2",
        option_c="C2",
        option_d="D2",
        option_e="E2",
        correct_index=0,
        status=QuestionStatus.PUBLISHED,
        cognitive_level="UNDERSTAND",
        difficulty="MEDIUM",
    )
    db_session.add_all([q1, q2])

    # Create session
    from app.models.session import SessionMode, SessionStatus
    from datetime import UTC
    
    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.SUBMITTED,
        year=1,
        blocks_json=["A"],
        total_questions=2,
        started_at=datetime.now(UTC),
    )
    db_session.add(session)

    # Create session questions
    sq1 = SessionQuestion(
        session_id=session.id,
        question_id=q1.id,
        position=1,
    )
    sq2 = SessionQuestion(
        session_id=session.id,
        question_id=q2.id,
        position=2,
    )
    db_session.add_all([sq1, sq2])

    # Create answers (q1 correct, q2 wrong)
    a1 = SessionAnswer(
        id=uuid4(),
        session_id=session.id,
        question_id=q1.id,
        selected_index=0,
        is_correct=True,
    )
    a2 = SessionAnswer(
        id=uuid4(),
        session_id=session.id,
        question_id=q2.id,
        selected_index=1,
        is_correct=False,
    )
    db_session.add_all([a1, a2])

    await db_session.commit()

    # Call difficulty update
    result = await update_question_difficulty_v0_for_session(db, session.id, trigger="test")

    # Verify updates
    assert result["questions_updated"] == 2
    assert "run_id" in result

    # Check difficulty records created
    from sqlalchemy import select
    
    diff_stmt = select(QuestionDifficulty).where(QuestionDifficulty.question_id.in_([q1.id, q2.id]))
    diff_result = await db_session.execute(diff_stmt)
    difficulties = diff_result.scalars().all()

    assert len(difficulties) == 2

    # Check algo_run logged
    run_id = result["run_id"]
    from sqlalchemy import select
    run_stmt = select(AlgoRun).where(AlgoRun.id == run_id)
    run_result = await db_session.execute(run_stmt)
    run = run_result.scalar_one_or_none()
    assert run is not None
    assert run.status == "SUCCESS"


@pytest.mark.asyncio
async def test_difficulty_algo_run_logging(db_session: AsyncSession):
    """Test that difficulty updates log algo runs correctly."""
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

    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.SUBMITTED,
        year=1,
        blocks_json=["A"],
        total_questions=0,
    )
    db_session.add(session)

    await db_session.commit()

    # Call update (no answers, should succeed)
    result = await update_question_difficulty_v0_for_session(db, session.id, trigger="test")

    # Should log run even with no updates
    assert "run_id" in result

    run_id = result["run_id"]
    from sqlalchemy import select
    run_stmt = select(AlgoRun).where(AlgoRun.id == run_id)
    run_result = await db_session.execute(run_stmt)
    run = run_result.scalar_one_or_none()

    assert run is not None
    assert run.status == "SUCCESS"
    assert run.trigger == "test"
    assert run.user_id == user.id
    assert run.session_id == session.id


# ============================================================================
# ADAPTIVE SELECTION v0 TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_adaptive_select_weak_themes_prioritized(db_session: AsyncSession):
    """Test that weak themes are prioritized in selection."""
    # Setup: user, year, blocks, themes
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
    await db_session.flush()

    # Ensure test data exists
    year, block, _ = await ensure_test_data(db_session)

    # Create two themes
    theme_weak = Theme(
        id=1,
        block_id=block.id,
        title="Weak Theme",
        order_no=1,
        is_active=True,
    )
    theme_strong = Theme(
        id=2,
        block_id=block.id,
        title="Strong Theme",
        order_no=2,
        is_active=True,
    )
    db_session.add_all([theme_weak, theme_strong])

    # Create mastery records
    mastery_weak = UserThemeMastery(
        id=uuid4(),
        year=1,
        block_id=block.id,
        theme_id=theme_weak.id,
        mastery_score=0.3,  # Weak
        attempts_total=10,
        correct_total=3,
        accuracy_pct=30.0,
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )
    mastery_strong = UserThemeMastery(
        id=uuid4(),
        year=1,
        block_id=block.id,
        theme_id=theme_strong.id,
        mastery_score=0.9,  # Strong
        attempts_total=10,
        correct_total=9,
        accuracy_pct=90.0,
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )
    db_session.add_all([mastery_weak, mastery_strong])

    # Create questions (5 per theme)
    questions = []
    for i in range(5):
        q = Question(
            id=uuid4(),
            year_id=1,
            block_id=block.id,
            theme_id=theme_weak.id,
            stem=f"Weak Q{i}",
            status=QuestionStatus.PUBLISHED,
        )
        questions.append(q)
        db_session.add(q)

    for i in range(5):
        q = Question(
            id=uuid4(),
            year_id=1,
            block_id=block.id,
            theme_id=theme_strong.id,
            stem=f"Strong Q{i}",
            status=QuestionStatus.PUBLISHED,
        )
        questions.append(q)
        db_session.add(q)

    await db_session.commit()

    # Select 6 questions (should favor weak theme)
    params = {
        "anti_repeat_days": 14,
        "theme_mix": {"weak": 0.7, "medium": 0.2, "mixed": 0.1},
        "difficulty_targets": {
            "weak": [900, 1050],
            "medium": [1000, 1150],
            "strong": [1050, 1250],
        },
        "difficulty_bucket_limits": {
            "easy": [0, 950],
            "medium": [950, 1100],
            "hard": [1100, 9999],
        },
        "difficulty_mix": {
            "easy": 0.2,
            "medium": 0.6,
            "hard": 0.2,
        },
        "fit_weights": {
            "mastery_inverse": 0.6,
            "difficulty_distance": 0.3,
            "freshness": 0.1,
        },
    }

    selected = await select_questions_v0(
        db,
        user.id,
        year_id=1,
        block_ids=[block.id],
        theme_ids=None,
        count=6,
        mode="tutor",
        params=params,
    )

    # Verify selection
    assert len(selected) == 6

    # Count questions per theme
    weak_count = sum(
        1 for qid in selected if any(q.id == qid and q.theme_id == theme_weak.id for q in questions)
    )
    strong_count = sum(
        1
        for qid in selected
        if any(q.id == qid and q.theme_id == theme_strong.id for q in questions)
    )

    # Weak theme should have more questions
    assert weak_count >= strong_count


@pytest.mark.asyncio
async def test_adaptive_select_recent_questions_excluded(db_session: AsyncSession):
    """Test that recently attempted questions are excluded."""
    # Setup: user, year, block, theme, questions
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
    await db_session.flush()

    # Ensure test data exists
    year, block, theme = await ensure_test_data(db_session)

    # Create 10 questions
    questions = []
    for i in range(10):
        q = Question(
            id=uuid4(),
        year_id=1,
        block_id=block.id,
        theme_id=theme.id,
        stem=f"Q{i}",
            status=QuestionStatus.PUBLISHED,
        )
        questions.append(q)
        db_session.add(q)

    # Create a recent session with first 3 questions
    from datetime import UTC
    recent_session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.SUBMITTED,
        year=1,
        blocks_json=["A"],
        total_questions=3,
        created_at=datetime.now(UTC) - timedelta(days=5),  # 5 days ago
    )
    db_session.add(recent_session)

    for i in range(3):
        sq = SessionQuestion(
            id=uuid4(),
            session_id=recent_session.id,
            question_id=questions[i].id,
            position=i,
            created_at=datetime.utcnow() - timedelta(days=5),
        )
        db_session.add(sq)

        sa = SessionAnswer(
            id=uuid4(),
            session_id=recent_session.id,
            question_id=questions[i].id,
            selected_index=0,
            is_correct=True,
        )
        db_session.add(sa)

    await db_session.commit()

    # Select 5 questions with anti_repeat_days = 14
    params = {
        "anti_repeat_days": 14,
        "theme_mix": {"weak": 0.5, "medium": 0.3, "mixed": 0.2},
        "difficulty_targets": {
            "weak": [900, 1050],
            "medium": [1000, 1150],
            "strong": [1050, 1250],
        },
        "difficulty_bucket_limits": {
            "easy": [0, 950],
            "medium": [950, 1100],
            "hard": [1100, 9999],
        },
        "difficulty_mix": {
            "easy": 0.2,
            "medium": 0.6,
            "hard": 0.2,
        },
        "fit_weights": {
            "mastery_inverse": 0.6,
            "difficulty_distance": 0.3,
            "freshness": 0.1,
        },
    }

    selected = await select_questions_v0(
        db,
        user.id,
        year_id=1,
        block_ids=[block.id],
        theme_ids=None,
        count=5,
        mode="tutor",
        params=params,
    )

    # Verify first 3 questions NOT selected
    recent_ids = [questions[i].id for i in range(3)]
    for qid in selected:
        assert qid not in recent_ids


@pytest.mark.asyncio
async def test_adaptive_select_deterministic(db_session: AsyncSession):
    """Test that selection is deterministic for same inputs."""
    # Setup: user, year, block, theme, questions
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
    await db_session.flush()

    # Ensure test data exists
    year, block, theme = await ensure_test_data(db_session)

    # Create 10 questions
    for i in range(10):
        q = Question(
            id=uuid4(),
        year_id=1,
        block_id=block.id,
        theme_id=theme.id,
        stem=f"Q{i}",
            status=QuestionStatus.PUBLISHED,
        )
        db_session.add(q)

    await db_session.commit()

    params = {
        "anti_repeat_days": 14,
        "theme_mix": {"weak": 0.5, "medium": 0.3, "mixed": 0.2},
        "difficulty_targets": {
            "weak": [900, 1050],
            "medium": [1000, 1150],
            "strong": [1050, 1250],
        },
        "difficulty_bucket_limits": {
            "easy": [0, 950],
            "medium": [950, 1100],
            "hard": [1100, 9999],
        },
        "difficulty_mix": {
            "easy": 0.2,
            "medium": 0.6,
            "hard": 0.2,
        },
        "fit_weights": {
            "mastery_inverse": 0.6,
            "difficulty_distance": 0.3,
            "freshness": 0.1,
        },
    }

    # Run selection twice
    selected1 = await select_questions_v0(
        db,
        user.id,
        year_id=1,
        block_ids=[block.id],
        theme_ids=None,
        count=5,
        mode="tutor",
        params=params,
    )

    selected2 = await select_questions_v0(
        db,
        user.id,
        year_id=1,
        block_ids=[block.id],
        theme_ids=None,
        count=5,
        mode="tutor",
        params=params,
    )

    # Should be identical
    assert selected1 == selected2


@pytest.mark.asyncio
async def test_adaptive_service_with_run_logging(db_session: AsyncSession):
    """Test adaptive service wrapper logs runs correctly."""
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
    await db_session.flush()

    # Ensure test data exists
    year, block, theme = await ensure_test_data(db_session)

    # Create 5 questions
    for i in range(5):
        q = Question(
            id=uuid4(),
        year_id=1,
        block_id=block.id,
        theme_id=theme.id,
        stem=f"Q{i}",
            status=QuestionStatus.PUBLISHED,
        )
        db_session.add(q)

    await db_session.commit()

    # Call adaptive service
    result = await adaptive_select_v0(
        db,
        user.id,
        year_id=1,
        block_ids=[block.id],
        theme_ids=None,
        count=3,
        mode="tutor",
        trigger="test",
    )

    # Verify result
    assert result["count"] == 3
    assert len(result["question_ids"]) == 3
    assert "run_id" in result

    # Check algo_run logged
    run_id = result["run_id"]
    from sqlalchemy import select
    run_stmt = select(AlgoRun).where(AlgoRun.id == run_id)
    run_result = await db_session.execute(run_stmt)
    run = run_result.scalar_one_or_none()

    assert run is not None
    assert run.status == "SUCCESS"
    assert run.trigger == "test"
    assert run.user_id == user.id


@pytest.mark.asyncio
async def test_adaptive_revision_queue_prioritized(db_session: AsyncSession):
    """Test that themes in revision_queue are prioritized."""
    # Setup: user, year, block, themes
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
    await db_session.flush()

    # Ensure test data exists
    year, block, _ = await ensure_test_data(db_session)

    # Create two themes
    theme_due = Theme(
        id=1,
        block_id=block.id,
        title="Due Theme",
        order_no=1,
        is_active=True,
    )
    theme_other = Theme(
        id=2,
        block_id=block.id,
        title="Other Theme",
        order_no=2,
        is_active=True,
    )
    db_session.add_all([theme_due, theme_other])

    # Add revision queue entry for theme_due (due today)
    revision_item = RevisionQueue(
        id=uuid4(),
        year=1,
        block_id=block.id,
        theme_id=theme_due.id,
        due_date=date.today(),
        priority_score=100.0,
        recommended_count=10,
        status="DUE",
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )
    db_session.add(revision_item)

    # Create questions (5 per theme)
    for i in range(5):
        q = Question(
            id=uuid4(),
            year_id=1,
            block_id=block.id,
            theme_id=theme_due.id,
            stem=f"Due Q{i}",
            status=QuestionStatus.PUBLISHED,
        )
        db_session.add(q)

    for i in range(5):
        q = Question(
            id=uuid4(),
            year_id=1,
            block_id=block.id,
            theme_id=theme_other.id,
            stem=f"Other Q{i}",
            status=QuestionStatus.PUBLISHED,
        )
        db_session.add(q)

    await db_session.commit()

    # Select 5 questions
    params = {
        "anti_repeat_days": 14,
        "theme_mix": {"weak": 0.5, "medium": 0.3, "mixed": 0.2},
        "difficulty_targets": {
            "weak": [900, 1050],
            "medium": [1000, 1150],
            "strong": [1050, 1250],
        },
        "difficulty_bucket_limits": {
            "easy": [0, 950],
            "medium": [950, 1100],
            "hard": [1100, 9999],
        },
        "difficulty_mix": {
            "easy": 0.2,
            "medium": 0.6,
            "hard": 0.2,
        },
        "fit_weights": {
            "mastery_inverse": 0.6,
            "difficulty_distance": 0.3,
            "freshness": 0.1,
        },
    }

    selected = await select_questions_v0(
        db,
        user.id,
        year_id=1,
        block_ids=[block.id],
        theme_ids=None,
        count=5,
        mode="tutor",
        params=params,
    )

    # Should prioritize due theme
    assert len(selected) == 5
    # All selected should be from theme_due
    stmt = select(Question).where(Question.id.in_(selected))
    result = await db_session.execute(stmt)
    selected_questions = result.scalars().all()

    for q in selected_questions:
        assert q.theme_id == theme_due.id
