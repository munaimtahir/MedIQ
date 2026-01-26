"""Tests for Learning Engine API endpoints."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_mastery import UserThemeMastery
from app.models.mistakes import MistakeLog
from app.models.question_cms import Question
from app.models.session import SessionAnswer, SessionQuestion, TestSession
from app.models.syllabus import Year, Block, Theme
from app.models.user import User

# ============================================================================
# RBAC & OWNERSHIP TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_student_cannot_recompute_mastery_for_another_user(db_session: AsyncSession):
    """Test that students can only recompute mastery for themselves."""
    from app.core.security import hash_password
    from app.models.user import UserRole
    
    # Create two students
    student1 = User(
        id=uuid4(),
        email="student1@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Student One",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    student2 = User(
        id=uuid4(),
        email="student2@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Student Two",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db_session.add_all([student1, student2])
    await db_session.flush()

    # Try to recompute mastery for student2 as student1
    from app.api.v1.endpoints.learning import assert_user_scope

    with pytest.raises(Exception) as exc_info:
        assert_user_scope(student2.id, student1)

    assert "Students can only access their own data" in str(exc_info.value)


@pytest.mark.asyncio
async def test_admin_can_recompute_mastery_for_another_user(db_session: AsyncSession):
    """Test that admins can recompute mastery for any user."""
    # Create admin and student
    admin = User(
        id=uuid4(),
        email="admin@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test Admin",
        role=UserRole.ADMIN.value,
        is_active=True,
        email_verified=True,
    )
    student = User(
        id=uuid4(),
        email="student@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db_session.add_all([admin, student])
    await db_session.flush()

    # Admin can specify another user
    from app.api.v1.endpoints.learning import assert_user_scope

    effective_user_id = assert_user_scope(student.id, admin)
    assert effective_user_id == student.id


@pytest.mark.asyncio
async def test_session_ownership_enforced_for_student(db_session: AsyncSession):
    """Test that students can only access their own sessions."""
    # Create two students
    student1 = User(
        id=uuid4(),
        email="student1@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    student2 = User(
        id=uuid4(),
        email="student2@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db_session.add_all([student1, student2])

    # Create session owned by student2
    session = TestSession(
        id=uuid4(),
        user_id=student2.id,
        mode="TUTOR",
        status="SUBMITTED",
        count=0,
    )
    db_session.add(session)
    await db_session.flush()

    # Student1 tries to access student2's session
    from app.api.v1.endpoints.learning import assert_session_ownership

    with pytest.raises(Exception) as exc_info:
        await assert_session_ownership(db, session.id, student1)

    assert "Not authorized" in str(exc_info.value)


@pytest.mark.asyncio
async def test_admin_can_access_any_session(db_session: AsyncSession):
    """Test that admins can access any session."""
    # Create admin and student
    admin = User(
        id=uuid4(),
        email="admin@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test Admin",
        role=UserRole.ADMIN.value,
        is_active=True,
        email_verified=True,
    )
    student = User(
        id=uuid4(),
        email="student@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db_session.add_all([admin, student])

    # Create session owned by student
    session = TestSession(
        id=uuid4(),
        user_id=student.id,
        mode="TUTOR",
        status="SUBMITTED",
        count=0,
    )
    db_session.add(session)
    await db_session.flush()

    # Admin can access student's session
    from app.api.v1.endpoints.learning import assert_session_ownership

    result = await assert_session_ownership(db, session.id, admin)
    assert result.id == session.id


# ============================================================================
# IDEMPOTENCY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_difficulty_update_idempotency(db_session: AsyncSession):
    """Test that calling difficulty update twice doesn't duplicate records."""
    # Setup: user, question, session, answer
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

    question = Question(
        id=uuid4(),
        year=1,
        block_id=uuid4(),
        theme_id=uuid4(),
        stem_text="Q1",
        status="PUBLISHED",
    )
    db_session.add(question)

    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode="TUTOR",
        status="SUBMITTED",
        count=1,
        submitted_at=datetime.utcnow(),
    )
    db_session.add(session)

    sq = SessionQuestion(
        id=uuid4(),
        session_id=session.id,
        question_id=question.id,
        order_index=0,
    )
    db_session.add(sq)

    answer = SessionAnswer(
        id=uuid4(),
        session_id=session.id,
        user_id=user.id,
        question_id=question.id,
        selected_index=0,
        is_correct=True,
        changed_count=0,
    )
    db_session.add(answer)

    await db_session.flush()

    # Call difficulty update twice
    from app.learning_engine.difficulty.service import update_question_difficulty_v0_for_session

    result1 = await update_question_difficulty_v0_for_session(db, session.id, trigger="test1")
    result2 = await update_question_difficulty_v0_for_session(db, session.id, trigger="test2")

    # Both succeed
    assert result1["questions_updated"] == 1
    assert result2["questions_updated"] == 1

    # Check only one difficulty record exists
    from app.models.learning_difficulty import QuestionDifficulty

    stmt = select(QuestionDifficulty).where(QuestionDifficulty.question_id == question.id)
    result = await db_session.execute(stmt)
    difficulties = result.scalars().all()

    assert len(difficulties) == 1  # Not duplicated


@pytest.mark.asyncio
async def test_mistakes_classify_idempotency(db_session: AsyncSession):
    """Test that calling mistakes classify twice doesn't duplicate records."""
    # Setup: user, question, session, wrong answer
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

    question = Question(
        id=uuid4(),
        year=1,
        block_id=uuid4(),
        theme_id=uuid4(),
        stem_text="Q1",
        status="PUBLISHED",
    )
    db_session.add(question)

    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        mode="TUTOR",
        status="SUBMITTED",
        count=1,
        submitted_at=datetime.utcnow(),
    )
    db_session.add(session)

    sq = SessionQuestion(
        id=uuid4(),
        session_id=session.id,
        question_id=question.id,
        order_index=0,
    )
    db_session.add(sq)

    answer = SessionAnswer(
        id=uuid4(),
        session_id=session.id,
        user_id=user.id,
        question_id=question.id,
        selected_index=1,
        is_correct=False,  # Wrong
        changed_count=0,
    )
    db_session.add(answer)

    await db_session.flush()

    # Call mistakes classify twice
    from app.learning_engine.mistakes.service import classify_mistakes_v0_for_session

    result1 = await classify_mistakes_v0_for_session(db, session.id, trigger="test1")
    result2 = await classify_mistakes_v0_for_session(db, session.id, trigger="test2")

    # Both succeed
    assert result1["classified"] == 1
    assert result2["classified"] == 1

    # Check only one mistake_log record exists
    stmt = select(MistakeLog).where(
        MistakeLog.session_id == session.id,
        MistakeLog.question_id == question.id,
    )
    result = await db_session.execute(stmt)
    mistakes = result.scalars().all()

    assert len(mistakes) == 1  # Not duplicated


# ============================================================================
# RUN_ID TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_mastery_recompute_returns_run_id(db_session: AsyncSession):
    """Test that mastery recompute always returns run_id."""
    # Setup: user, year, block, theme
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

    block = Block(id=uuid4(), year=1, name="Block 1", order=1)
    db_session.add(block)

    theme = Theme(
        id=uuid4(),
        year=1,
        block_id=block.id,
        name="Theme 1",
        order=1,
    )
    db_session.add(theme)

    await db_session.flush()

    # Call mastery recompute
    from app.learning_engine.mastery.service import recompute_mastery_v0_for_user

    result = await recompute_mastery_v0_for_user(db, user_id=user.id)

    # Verify run_id present
    assert "run_id" in result
    assert result["run_id"] is not None


@pytest.mark.asyncio
async def test_revision_plan_returns_run_id(db_session: AsyncSession):
    """Test that revision plan always returns run_id."""
    # Setup: user, year, block
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

    block = Block(id=uuid4(), year=1, name="Block 1", order=1)
    db_session.add(block)

    await db_session.flush()

    # Call revision plan
    from app.learning_engine.revision.service import generate_revision_queue_v0

    result = await generate_revision_queue_v0(
        db,
        user_id=user.id,
        year=1,
        block_id=None,
        trigger="test",
    )

    # Verify run_id present
    assert "run_id" in result
    assert result["run_id"] is not None


@pytest.mark.asyncio
async def test_adaptive_select_returns_run_id(db_session: AsyncSession):
    """Test that adaptive select always returns run_id."""
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

    year = Year(id=1, name="1st Year", order_no=1, is_active=True)
    db_session.add(year)

    block = Block(id=uuid4(), year=1, name="Block 1", order=1)
    db_session.add(block)

    theme = Theme(
        id=uuid4(),
        year=1,
        block_id=block.id,
        name="Theme 1",
        order=1,
    )
    db_session.add(theme)

    # Create questions
    for i in range(5):
        q = Question(
            id=uuid4(),
            year=1,
            block_id=block.id,
            theme_id=theme.id,
            stem_text=f"Q{i}",
            status="PUBLISHED",
        )
        db_session.add(q)

    await db_session.flush()

    # Call adaptive select
    from app.learning_engine.adaptive.service import adaptive_select_v0

    result = await adaptive_select_v0(
        db,
        user_id=user.id,
        year=1,
        block_ids=[block.id],
        theme_ids=None,
        count=3,
        mode="tutor",
        trigger="test",
    )

    # Verify run_id present
    assert "run_id" in result
    assert result["run_id"] is not None


# ============================================================================
# FUNCTIONAL TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_mastery_recompute_dry_run(db_session: AsyncSession):
    """Test that dry_run doesn't write to database."""
    # Setup: user, year, block, theme
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

    block = Block(id=uuid4(), year=1, name="Block 1", order=1)
    db_session.add(block)

    theme = Theme(
        id=uuid4(),
        year=1,
        block_id=block.id,
        name="Theme 1",
        order=1,
    )
    db_session.add(theme)

    await db_session.flush()

    # Call with dry_run=True
    from app.learning_engine.mastery.service import recompute_mastery_v0_for_user

    await recompute_mastery_v0_for_user(
        db,
        user_id=user.id,
        dry_run=True,
    )

    # Verify no records written
    stmt = select(UserThemeMastery).where(UserThemeMastery.user_id == user.id)
    mastery_result = await db_session.execute(stmt)
    mastery_records = mastery_result.scalars().all()

    assert len(mastery_records) == 0  # Dry run doesn't write


@pytest.mark.asyncio
async def test_adaptive_select_deterministic(db: AsyncSession):
    """Test that adaptive select returns same results for same inputs."""
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

    year = Year(id=1, name="1st Year", order_no=1, is_active=True)
    db_session.add(year)

    block = Block(id=uuid4(), year=1, name="Block 1", order=1)
    db_session.add(block)

    theme = Theme(
        id=uuid4(),
        year=1,
        block_id=block.id,
        name="Theme 1",
        order=1,
    )
    db_session.add(theme)

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
        db_session.add(q)

    await db_session.flush()

    # Call adaptive select twice with same inputs
    from app.learning_engine.adaptive.service import adaptive_select_v0

    result1 = await adaptive_select_v0(
        db,
        user_id=user.id,
        year=1,
        block_ids=[block.id],
        theme_ids=None,
        count=5,
        mode="tutor",
        trigger="test",
    )

    result2 = await adaptive_select_v0(
        db,
        user_id=user.id,
        year=1,
        block_ids=[block.id],
        theme_ids=None,
        count=5,
        mode="tutor",
        trigger="test",
    )

    # Results should be identical (deterministic)
    assert result1["question_ids"] == result2["question_ids"]


@pytest.mark.asyncio
async def test_user_scope_defaults_to_current_user(db: AsyncSession):
    """Test that omitting user_id defaults to current user."""
    # Create student
    student = User(
        id=uuid4(),
        email="student@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db_session.add(student)
    await db_session.flush()

    # Call with user_id=None
    from app.api.v1.endpoints.learning import assert_user_scope

    effective_user_id = assert_user_scope(None, student)

    # Should default to current user
    assert effective_user_id == student.id
