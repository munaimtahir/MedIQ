"""Tests for Difficulty Calibration v0 and Adaptive Selection v0."""

import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.difficulty.service import (
    compute_elo_update,
    compute_student_rating,
    update_question_difficulty_v0_for_session,
)
from app.learning_engine.adaptive.v0 import select_questions_v0
from app.learning_engine.adaptive.service import adaptive_select_v0
from app.models.learning import AlgoRun, AlgoVersion, AlgoParams
from app.models.learning_difficulty import QuestionDifficulty
from app.models.learning_mastery import UserThemeMastery
from app.models.learning_revision import RevisionQueue
from app.models.question_cms import Question
from app.models.session import SessionAnswer, SessionQuestion, TestSession
from app.models.syllabus import AcademicYear, Block, Theme
from app.models.user import User


# ============================================================================
# DIFFICULTY CALIBRATION v0 TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_compute_elo_update_basic():
    """Test ELO update formula basics."""
    # Question rated 1000, student rated 1000, correct answer
    new_rating, delta, expected = compute_elo_update(
        question_rating=1000,
        student_rating=1000,
        actual=1,
        k_factor=16,
        rating_scale=400,
    )
    
    # Expected should be 0.5 (even match)
    assert abs(expected - 0.5) < 0.01
    
    # Delta should be positive (question gets harder)
    assert delta > 0
    assert abs(delta - 8.0) < 0.1  # 16 * (1 - 0.5) = 8
    
    # New rating increased
    assert new_rating > 1000


@pytest.mark.asyncio
async def test_compute_elo_update_weak_student_correct():
    """Test that correct answer by weak student increases difficulty."""
    # Weak student (800) gets question right (rated 1000)
    new_rating, delta, expected = compute_elo_update(
        question_rating=1000,
        student_rating=800,
        actual=1,
        k_factor=16,
        rating_scale=400,
    )
    
    # Expected < 0.5 (student weaker than question)
    assert expected < 0.5
    
    # Large positive delta (question is easier than thought)
    assert delta > 8  # More than neutral case
    
    # Question rating decreases (easier)
    assert new_rating > 1000


@pytest.mark.asyncio
async def test_compute_elo_update_strong_student_wrong():
    """Test that wrong answer by strong student decreases difficulty."""
    # Strong student (1200) gets question wrong (rated 1000)
    new_rating, delta, expected = compute_elo_update(
        question_rating=1000,
        student_rating=1200,
        actual=0,
        k_factor=16,
        rating_scale=400,
    )
    
    # Expected > 0.5 (student stronger than question)
    assert expected > 0.5
    
    # Negative delta (question is easier than thought)
    assert delta < 0
    
    # Question rating decreases (easier)
    assert new_rating < 1000


@pytest.mark.asyncio
async def test_compute_student_rating_fixed():
    """Test fixed student rating strategy."""
    params = {"baseline_rating": 1000}
    
    rating = compute_student_rating("fixed", params, mastery_score=0.8)
    
    # Ignores mastery, returns baseline
    assert rating == 1000


@pytest.mark.asyncio
async def test_compute_student_rating_mastery_mapped():
    """Test mastery-mapped student rating strategy."""
    params = {
        "baseline_rating": 1000,
        "mastery_rating_map": {"min": 800, "max": 1200}
    }
    
    # Weak student
    rating = compute_student_rating("mastery_mapped", params, mastery_score=0.0)
    assert rating == 800
    
    # Medium student
    rating = compute_student_rating("mastery_mapped", params, mastery_score=0.5)
    assert rating == 1000
    
    # Strong student
    rating = compute_student_rating("mastery_mapped", params, mastery_score=1.0)
    assert rating == 1200
    
    # No mastery available
    rating = compute_student_rating("mastery_mapped", params, mastery_score=None)
    assert rating == 1000  # Falls back to baseline


@pytest.mark.asyncio
async def test_difficulty_update_on_session_submit(db: AsyncSession):
    """Test difficulty update when session is submitted."""
    # Setup: Create user, year, block, theme, questions
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
    
    # Create questions
    q1 = Question(
        id=uuid4(),
        year=1,
        block_id=block.id,
        theme_id=theme.id,
        stem_text="Q1",
        status="PUBLISHED",
    )
    q2 = Question(
        id=uuid4(),
        year=1,
        block_id=block.id,
        theme_id=theme.id,
        stem_text="Q2",
        status="PUBLISHED",
    )
    db.add_all([q1, q2])
    
    # Create session
    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode="TUTOR",
        status="SUBMITTED",
        count=2,
    )
    db.add(session)
    
    # Create session questions
    sq1 = SessionQuestion(
        id=uuid4(),
        session_id=session.id,
        question_id=q1.id,
        order_index=0,
    )
    sq2 = SessionQuestion(
        id=uuid4(),
        session_id=session.id,
        question_id=q2.id,
        order_index=1,
    )
    db.add_all([sq1, sq2])
    
    # Create answers (q1 correct, q2 wrong)
    a1 = SessionAnswer(
        id=uuid4(),
        session_id=session.id,
        user_id=user.id,
        question_id=q1.id,
        selected_index=0,
        is_correct=True,
        changed_count=1,
    )
    a2 = SessionAnswer(
        id=uuid4(),
        session_id=session.id,
        user_id=user.id,
        question_id=q2.id,
        selected_index=1,
        is_correct=False,
        changed_count=1,
    )
    db.add_all([a1, a2])
    
    await db.commit()
    
    # Call difficulty update
    result = await update_question_difficulty_v0_for_session(
        db, session.id, trigger="test"
    )
    
    # Verify updates
    assert result["questions_updated"] == 2
    assert "run_id" in result
    
    # Check difficulty records created
    diff_stmt = select(QuestionDifficulty).where(
        QuestionDifficulty.question_id.in_([q1.id, q2.id])
    )
    diff_result = await db.execute(diff_stmt)
    difficulties = diff_result.scalars().all()
    
    assert len(difficulties) == 2
    
    # Check algo_run logged
    run_id = result["run_id"]
    run = await db.get(AlgoRun, run_id)
    assert run is not None
    assert run.status == "SUCCESS"


@pytest.mark.asyncio
async def test_difficulty_algo_run_logging(db: AsyncSession):
    """Test that difficulty updates log algo runs correctly."""
    # Setup minimal data
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
        count=0,
    )
    db.add(session)
    
    await db.commit()
    
    # Call update (no answers, should succeed)
    result = await update_question_difficulty_v0_for_session(
        db, session.id, trigger="test"
    )
    
    # Should log run even with no updates
    assert "run_id" in result
    
    run_id = result["run_id"]
    run = await db.get(AlgoRun, run_id)
    
    assert run is not None
    assert run.status == "SUCCESS"
    assert run.trigger == "test"
    assert run.user_id == user.id
    assert run.session_id == session.id


# ============================================================================
# ADAPTIVE SELECTION v0 TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_adaptive_select_weak_themes_prioritized(db: AsyncSession):
    """Test that weak themes are prioritized in selection."""
    # Setup: user, year, blocks, themes
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
    
    # Create two themes
    theme_weak = Theme(
        id=uuid4(),
        year=1,
        block_id=block.id,
        name="Weak Theme",
        order=1,
    )
    theme_strong = Theme(
        id=uuid4(),
        year=1,
        block_id=block.id,
        name="Strong Theme",
        order=2,
    )
    db.add_all([theme_weak, theme_strong])
    
    # Create mastery records
    mastery_weak = UserThemeMastery(
        id=uuid4(),
        user_id=user.id,
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
        user_id=user.id,
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
    db.add_all([mastery_weak, mastery_strong])
    
    # Create questions (5 per theme)
    questions = []
    for i in range(5):
        q = Question(
            id=uuid4(),
            year=1,
            block_id=block.id,
            theme_id=theme_weak.id,
            stem_text=f"Weak Q{i}",
            status="PUBLISHED",
        )
        questions.append(q)
        db.add(q)
    
    for i in range(5):
        q = Question(
            id=uuid4(),
            year=1,
            block_id=block.id,
            theme_id=theme_strong.id,
            stem_text=f"Strong Q{i}",
            status="PUBLISHED",
        )
        questions.append(q)
        db.add(q)
    
    await db.commit()
    
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
        year=1,
        block_ids=[block.id],
        theme_ids=None,
        count=6,
        mode="tutor",
        params=params,
    )
    
    # Verify selection
    assert len(selected) == 6
    
    # Count questions per theme
    weak_count = sum(1 for qid in selected if any(q.id == qid and q.theme_id == theme_weak.id for q in questions))
    strong_count = sum(1 for qid in selected if any(q.id == qid and q.theme_id == theme_strong.id for q in questions))
    
    # Weak theme should have more questions
    assert weak_count >= strong_count


@pytest.mark.asyncio
async def test_adaptive_select_recent_questions_excluded(db: AsyncSession):
    """Test that recently attempted questions are excluded."""
    # Setup: user, year, block, theme, questions
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
    
    # Create 10 questions
    questions = []
    for i in range(10):
        q = Question(
            id=uuid4(),
            year=1,
            block_id=block.id,
            theme_id=theme.id,
            stem_text=f"Q{i}",
            status="PUBLISHED",
        )
        questions.append(q)
        db.add(q)
    
    # Create a recent session with first 3 questions
    recent_session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode="TUTOR",
        status="SUBMITTED",
        count=3,
        created_at=datetime.utcnow() - timedelta(days=5),  # 5 days ago
    )
    db.add(recent_session)
    
    for i in range(3):
        sq = SessionQuestion(
            id=uuid4(),
            session_id=recent_session.id,
            question_id=questions[i].id,
            order_index=i,
            created_at=datetime.utcnow() - timedelta(days=5),
        )
        db.add(sq)
        
        sa = SessionAnswer(
            id=uuid4(),
            session_id=recent_session.id,
            user_id=user.id,
            question_id=questions[i].id,
            selected_index=0,
            is_correct=True,
            changed_count=1,
        )
        db.add(sa)
    
    await db.commit()
    
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
        year=1,
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
async def test_adaptive_select_deterministic(db: AsyncSession):
    """Test that selection is deterministic for same inputs."""
    # Setup: user, year, block, theme, questions
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
    
    # Create 10 questions
    for i in range(10):
        q = Question(
            id=uuid4(),
            year=1,
            block_id=block.id,
            theme_id=theme.id,
            stem_text=f"Q{i}",
            status="PUBLISHED",
        )
        db.add(q)
    
    await db.commit()
    
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
        year=1,
        block_ids=[block.id],
        theme_ids=None,
        count=5,
        mode="tutor",
        params=params,
    )
    
    selected2 = await select_questions_v0(
        db,
        user.id,
        year=1,
        block_ids=[block.id],
        theme_ids=None,
        count=5,
        mode="tutor",
        params=params,
    )
    
    # Should be identical
    assert selected1 == selected2


@pytest.mark.asyncio
async def test_adaptive_service_with_run_logging(db: AsyncSession):
    """Test adaptive service wrapper logs runs correctly."""
    # Setup minimal data
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
    
    # Create 5 questions
    for i in range(5):
        q = Question(
            id=uuid4(),
            year=1,
            block_id=block.id,
            theme_id=theme.id,
            stem_text=f"Q{i}",
            status="PUBLISHED",
        )
        db.add(q)
    
    await db.commit()
    
    # Call adaptive service
    result = await adaptive_select_v0(
        db,
        user.id,
        year=1,
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
    run = await db.get(AlgoRun, run_id)
    
    assert run is not None
    assert run.status == "SUCCESS"
    assert run.trigger == "test"
    assert run.user_id == user.id


@pytest.mark.asyncio
async def test_adaptive_revision_queue_prioritized(db: AsyncSession):
    """Test that themes in revision_queue are prioritized."""
    # Setup: user, year, block, themes
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
    
    # Create two themes
    theme_due = Theme(
        id=uuid4(),
        year=1,
        block_id=block.id,
        name="Due Theme",
        order=1,
    )
    theme_other = Theme(
        id=uuid4(),
        year=1,
        block_id=block.id,
        name="Other Theme",
        order=2,
    )
    db.add_all([theme_due, theme_other])
    
    # Add revision queue entry for theme_due (due today)
    revision_item = RevisionQueue(
        id=uuid4(),
        user_id=user.id,
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
    db.add(revision_item)
    
    # Create questions (5 per theme)
    for i in range(5):
        q = Question(
            id=uuid4(),
            year=1,
            block_id=block.id,
            theme_id=theme_due.id,
            stem_text=f"Due Q{i}",
            status="PUBLISHED",
        )
        db.add(q)
    
    for i in range(5):
        q = Question(
            id=uuid4(),
            year=1,
            block_id=block.id,
            theme_id=theme_other.id,
            stem_text=f"Other Q{i}",
            status="PUBLISHED",
        )
        db.add(q)
    
    await db.commit()
    
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
        year=1,
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
    result = await db.execute(stmt)
    selected_questions = result.scalars().all()
    
    for q in selected_questions:
        assert q.theme_id == theme_due.id
