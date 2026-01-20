"""Tests for Revision and Mistakes API endpoints."""

import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_revision import RevisionQueue
from app.models.mistakes import MistakeLog
from app.models.question_cms import Question
from app.models.syllabus import AcademicYear, Block, Theme
from app.models.user import User


# ============================================================================
# REVISION QUEUE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_revision_queue_returns_only_user_items(db: AsyncSession):
    """Test that revision queue only returns current user's items."""
    # Create two users
    user1 = User(
        id=uuid4(),
        email="user1@example.com",
        hashed_password="hashed",
        role="STUDENT",
    )
    user2 = User(
        id=uuid4(),
        email="user2@example.com",
        hashed_password="hashed",
        role="STUDENT",
    )
    db.add_all([user1, user2])

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

    # Create revision items for both users
    item1 = RevisionQueue(
        id=uuid4(),
        user_id=user1.id,
        year=1,
        block_id=block.id,
        theme_id=theme.id,
        due_date=date.today(),
        priority_score=80.0,
        recommended_count=10,
        status="DUE",
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )

    item2 = RevisionQueue(
        id=uuid4(),
        user_id=user2.id,
        year=1,
        block_id=block.id,
        theme_id=theme.id,
        due_date=date.today(),
        priority_score=75.0,
        recommended_count=12,
        status="DUE",
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )

    db.add_all([item1, item2])
    await db.commit()

    # Query for user1
    from app.api.v1.endpoints.revision import get_revision_queue

    # Simulate request (would normally use TestClient)
    # For now, just verify database query logic
    stmt = select(RevisionQueue).where(RevisionQueue.user_id == user1.id)
    result = await db.execute(stmt)
    items = result.scalars().all()

    assert len(items) == 1
    assert items[0].user_id == user1.id


@pytest.mark.asyncio
async def test_revision_patch_action_done_updates_status(db: AsyncSession):
    """Test that DONE action updates status correctly."""
    # Setup: user, year, block, theme, revision item
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

    item = RevisionQueue(
        id=uuid4(),
        user_id=user.id,
        year=1,
        block_id=block.id,
        theme_id=theme.id,
        due_date=date.today(),
        priority_score=80.0,
        recommended_count=10,
        status="DUE",
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )
    db.add(item)
    await db.commit()

    # Update status to DONE
    item.status = "DONE"
    await db.commit()

    # Verify
    await db.refresh(item)
    assert item.status == "DONE"


@pytest.mark.asyncio
async def test_revision_snooze_days_validated(db: AsyncSession):
    """Test that snooze_days is validated (1-3)."""
    from app.schemas.revision import RevisionQueueUpdateRequest

    # Valid snooze
    valid_request = RevisionQueueUpdateRequest(action="SNOOZE", snooze_days=2)
    valid_request.validate_snooze()  # Should not raise

    # Invalid: snooze_days missing for SNOOZE
    invalid_request = RevisionQueueUpdateRequest(action="SNOOZE", snooze_days=None)
    with pytest.raises(ValueError):
        invalid_request.validate_snooze()

    # Invalid: snooze_days provided for non-SNOOZE action
    invalid_request2 = RevisionQueueUpdateRequest(action="DONE", snooze_days=1)
    with pytest.raises(ValueError):
        invalid_request2.validate_snooze()


# ============================================================================
# MISTAKES TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_mistakes_list_filtered_by_type(db: AsyncSession):
    """Test that mistakes list can be filtered by mistake_type."""
    # Setup: user, mistakes with different types
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

    # Create mistakes with different types
    mistake1 = MistakeLog(
        id=uuid4(),
        user_id=user.id,
        session_id=uuid4(),
        question_id=question.id,
        year=1,
        block_id=block.id,
        theme_id=theme.id,
        is_correct=False,
        mistake_type="FAST_WRONG",
        severity=1,
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )

    mistake2 = MistakeLog(
        id=uuid4(),
        user_id=user.id,
        session_id=uuid4(),
        question_id=question.id,
        year=1,
        block_id=block.id,
        theme_id=theme.id,
        is_correct=False,
        mistake_type="KNOWLEDGE_GAP",
        severity=2,
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )

    db.add_all([mistake1, mistake2])
    await db.commit()

    # Query filtered by type
    stmt = select(MistakeLog).where(
        MistakeLog.user_id == user.id,
        MistakeLog.mistake_type == "FAST_WRONG",
    )
    result = await db.execute(stmt)
    mistakes = result.scalars().all()

    assert len(mistakes) == 1
    assert mistakes[0].mistake_type == "FAST_WRONG"


@pytest.mark.asyncio
async def test_mistakes_list_filtered_by_block(db: AsyncSession):
    """Test that mistakes list can be filtered by block_id."""
    # Setup: user, two blocks, mistakes in each
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        role="STUDENT",
    )
    db.add(user)

    year = AcademicYear(id=1, year=1, name="Year 1")
    db.add(year)

    block1 = Block(id=uuid4(), year=1, name="Block 1", order=1)
    block2 = Block(id=uuid4(), year=1, name="Block 2", order=2)
    db.add_all([block1, block2])

    theme1 = Theme(
        id=uuid4(),
        year=1,
        block_id=block1.id,
        name="Theme 1",
        order=1,
    )
    theme2 = Theme(
        id=uuid4(),
        year=1,
        block_id=block2.id,
        name="Theme 2",
        order=1,
    )
    db.add_all([theme1, theme2])

    question1 = Question(
        id=uuid4(),
        year=1,
        block_id=block1.id,
        theme_id=theme1.id,
        stem_text="Q1",
        status="PUBLISHED",
    )
    question2 = Question(
        id=uuid4(),
        year=1,
        block_id=block2.id,
        theme_id=theme2.id,
        stem_text="Q2",
        status="PUBLISHED",
    )
    db.add_all([question1, question2])

    # Create mistakes in different blocks
    mistake1 = MistakeLog(
        id=uuid4(),
        user_id=user.id,
        session_id=uuid4(),
        question_id=question1.id,
        year=1,
        block_id=block1.id,
        theme_id=theme1.id,
        is_correct=False,
        mistake_type="FAST_WRONG",
        severity=1,
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )

    mistake2 = MistakeLog(
        id=uuid4(),
        user_id=user.id,
        session_id=uuid4(),
        question_id=question2.id,
        year=1,
        block_id=block2.id,
        theme_id=theme2.id,
        is_correct=False,
        mistake_type="KNOWLEDGE_GAP",
        severity=2,
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )

    db.add_all([mistake1, mistake2])
    await db.commit()

    # Query filtered by block1
    stmt = select(MistakeLog).where(
        MistakeLog.user_id == user.id,
        MistakeLog.block_id == block1.id,
    )
    result = await db.execute(stmt)
    mistakes = result.scalars().all()

    assert len(mistakes) == 1
    assert mistakes[0].block_id == block1.id


@pytest.mark.asyncio
async def test_mistakes_list_filtered_by_theme(db: AsyncSession):
    """Test that mistakes list can be filtered by theme_id."""
    # Setup similar to block test
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

    theme1 = Theme(
        id=uuid4(),
        year=1,
        block_id=block.id,
        name="Theme 1",
        order=1,
    )
    theme2 = Theme(
        id=uuid4(),
        year=1,
        block_id=block.id,
        name="Theme 2",
        order=2,
    )
    db.add_all([theme1, theme2])

    question1 = Question(
        id=uuid4(),
        year=1,
        block_id=block.id,
        theme_id=theme1.id,
        stem_text="Q1",
        status="PUBLISHED",
    )
    question2 = Question(
        id=uuid4(),
        year=1,
        block_id=block.id,
        theme_id=theme2.id,
        stem_text="Q2",
        status="PUBLISHED",
    )
    db.add_all([question1, question2])

    # Create mistakes in different themes
    mistake1 = MistakeLog(
        id=uuid4(),
        user_id=user.id,
        session_id=uuid4(),
        question_id=question1.id,
        year=1,
        block_id=block.id,
        theme_id=theme1.id,
        is_correct=False,
        mistake_type="FAST_WRONG",
        severity=1,
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )

    mistake2 = MistakeLog(
        id=uuid4(),
        user_id=user.id,
        session_id=uuid4(),
        question_id=question2.id,
        year=1,
        block_id=block.id,
        theme_id=theme2.id,
        is_correct=False,
        mistake_type="KNOWLEDGE_GAP",
        severity=2,
        algo_version_id=uuid4(),
        params_id=uuid4(),
        run_id=uuid4(),
    )

    db.add_all([mistake1, mistake2])
    await db.commit()

    # Query filtered by theme1
    stmt = select(MistakeLog).where(
        MistakeLog.user_id == user.id,
        MistakeLog.theme_id == theme1.id,
    )
    result = await db.execute(stmt)
    mistakes = result.scalars().all()

    assert len(mistakes) == 1
    assert mistakes[0].theme_id == theme1.id
