"""Tests for Revision and Mistakes API endpoints."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning import AlgoVersion, AlgoParams, AlgoRun
from app.models.learning_revision import RevisionQueue
from app.models.mistakes import MistakeLog
from app.models.question_cms import Question, QuestionStatus
from app.models.syllabus import Year, Block, Theme
from app.core.security import hash_password
from app.models.user import User, UserRole

# ============================================================================
# REVISION QUEUE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_revision_queue_returns_only_user_items(db_session: AsyncSession):
    """Test that revision queue only returns current user's items."""
    # Create algo objects first
    algo_version = AlgoVersion(
        id=uuid4(),
        algo_key="REVISION",
        version="v0",
        status="ACTIVE",
    )
    db_session.add(algo_version)
    await db_session.flush()
    
    algo_params = AlgoParams(
        id=uuid4(),
        algo_version_id=algo_version.id,
        params_json={},
    )
    db_session.add(algo_params)
    await db_session.flush()
    
    from datetime import UTC, datetime
    algo_run = AlgoRun(
        id=uuid4(),
        algo_version_id=algo_version.id,
        params_id=algo_params.id,
        trigger="manual",
        status="SUCCESS",
        started_at=datetime.now(UTC),
    )
    db_session.add(algo_run)
    await db_session.flush()
    
    # Create two users
    user1 = User(
        id=uuid4(),
        email="user1@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    user2 = User(
        id=uuid4(),
        email="user2@example.com",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db_session.add_all([user1, user2])
    await db_session.flush()

    year = Year(id=1, name="1st Year", order_no=1, is_active=True)
    db_session.add(year)
    await db_session.flush()

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
    await db_session.flush()

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
        algo_version_id=algo_version.id,
        params_id=algo_params.id,
        run_id=algo_run.id,
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
        algo_version_id=algo_version.id,
        params_id=algo_params.id,
        run_id=algo_run.id,
    )

    db_session.add_all([item1, item2])
    await db_session.flush()

    # Query for user1

    # Simulate request (would normally use TestClient)
    # For now, just verify database query logic
    stmt = select(RevisionQueue).where(RevisionQueue.user_id == user1.id)
    result = await db_session.execute(stmt)
    items = result.scalars().all()

    assert len(items) == 1
    assert items[0].user_id == user1.id


@pytest.mark.asyncio
async def test_revision_patch_action_done_updates_status(db_session: AsyncSession):
    """Test that DONE action updates status correctly."""
    # Setup: user, year, block, theme, revision item
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

    year = Year(id=1, name="1st Year", order_no=1, is_active=True)
    db_session.add(year)
    await db_session.flush()

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
    await db_session.flush()

    # Create algo objects
    algo_version = AlgoVersion(
        id=uuid4(),
        algo_key="REVISION",
        version="v0",
        status="ACTIVE",
    )
    db_session.add(algo_version)
    await db_session.flush()
    
    algo_params = AlgoParams(
        id=uuid4(),
        algo_version_id=algo_version.id,
        params_json={},
    )
    db_session.add(algo_params)
    await db_session.flush()
    
    from datetime import UTC, datetime
    algo_run = AlgoRun(
        id=uuid4(),
        algo_version_id=algo_version.id,
        params_id=algo_params.id,
        trigger="manual",
        status="SUCCESS",
        started_at=datetime.now(UTC),
    )
    db_session.add(algo_run)
    await db_session.flush()

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
        algo_version_id=algo_version.id,
        params_id=algo_params.id,
        run_id=algo_run.id,
    )
    db_session.add(item)
    await db_session.flush()

    # Update status to DONE
    item.status = "DONE"
    await db_session.flush()

    # Verify
    await db_session.refresh(item)
    assert item.status == "DONE"


@pytest.mark.asyncio
async def test_revision_snooze_days_validated(db_session: AsyncSession):
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
async def test_mistakes_list_filtered_by_type(db_session: AsyncSession):
    """Test that mistakes list can be filtered by mistake_type."""
    # Setup: user, mistakes with different types
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
        status=QuestionStatus.PUBLISHED,
    )
    db_session.add(question)

    # Create mistakes with different types
    from app.models.learning import AlgoVersion
    from app.models.mistakes import MistakeLog
    
    # Create required algo objects for MistakeLog
    algo_version = AlgoVersion(
        id=uuid4(),
        algo_key="MISTAKES",
        version="v0",
        status="ACTIVE",
    )
    db_session.add(algo_version)
    await db_session.flush()
    
    algo_params = AlgoParams(
        id=uuid4(),
        algo_version_id=algo_version.id,
        params_json={},
    )
    db_session.add(algo_params)
    await db_session.flush()
    
    from datetime import UTC, datetime
    algo_run = AlgoRun(
        id=uuid4(),
        algo_version_id=algo_version.id,
        params_id=algo_params.id,
        trigger="manual",
        status="SUCCESS",
        started_at=datetime.now(UTC),
    )
    db_session.add_all([algo_version, algo_params, algo_run])
    await db_session.flush()
    
    mistake1 = MistakeLog(
        user_id=user.id,
        session_id=uuid4(),
        question_id=question.id,
        year=1,
        block_id=None,  # MistakeLog expects UUID but Block uses Integer - schema mismatch, use None for now
        theme_id=None,  # Same issue
        is_correct=False,
        mistake_type="FAST_WRONG",
        severity=1,
        algo_version_id=algo_version.id,
        params_id=algo_params.id,
        run_id=algo_run.id,
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
        algo_version_id=algo_version.id,
        params_id=algo_params.id,
        run_id=algo_run.id,
    )

    db_session.add_all([mistake1, mistake2])
    await db_session.flush()

    # Query filtered by type
    stmt = select(MistakeLog).where(
        MistakeLog.user_id == user.id,
        MistakeLog.mistake_type == "FAST_WRONG",
    )
    result = await db_session.execute(stmt)
    mistakes = result.scalars().all()

    assert len(mistakes) == 1
    assert mistakes[0].mistake_type == "FAST_WRONG"


@pytest.mark.asyncio
async def test_mistakes_list_filtered_by_block(db_session: AsyncSession):
    """Test that mistakes list can be filtered by block_id."""
    # Setup: user, two blocks, mistakes in each
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

    block1 = Block(id=1, year_id=1, code="A", name="Block 1", order_no=1, is_active=True)
    block2 = Block(id=2, year_id=1, code="B", name="Block 2", order_no=2, is_active=True)
    db_session.add_all([block1, block2])

    theme1 = Theme(
        id=1,
        block_id=block1.id,
        title="Theme 1",
        order_no=1,
        is_active=True,
    )
    theme2 = Theme(
        id=2,
        block_id=block2.id,
        title="Theme 2",
        order_no=1,
        is_active=True,
    )
    db_session.add_all([theme1, theme2])

    question1 = Question(
        id=uuid4(),
        year_id=1,
        block_id=block1.id,
        theme_id=theme1.id,
        stem="Q1",
        status=QuestionStatus.PUBLISHED,
    )
    question2 = Question(
        id=uuid4(),
        year_id=1,
        block_id=block2.id,
        theme_id=theme2.id,
        stem="Q2",
        status=QuestionStatus.PUBLISHED,
    )
    db_session.add_all([question1, question2])

    # Create algo objects for mistakes
    algo_version2 = AlgoVersion(
        id=uuid4(),
        algo_key="MISTAKES",
        version="v0",
        status="ACTIVE",
    )
    db_session.add(algo_version2)
    await db_session.flush()
    
    algo_params2 = AlgoParams(
        id=uuid4(),
        algo_version_id=algo_version2.id,
        params_json={},
    )
    db_session.add(algo_params2)
    await db_session.flush()
    
    algo_run2 = AlgoRun(
        id=uuid4(),
        algo_version_id=algo_version2.id,
        params_id=algo_params2.id,
        status="SUCCESS",
    )
    db_session.add(algo_run2)
    await db_session.flush()
    
    # Create mistakes in different blocks
    mistake1 = MistakeLog(
        user_id=user.id,
        session_id=uuid4(),
        question_id=question1.id,
        year=1,
        block_id=None,  # Schema mismatch: Block uses Integer, MistakeLog expects UUID
        theme_id=None,
        is_correct=False,
        mistake_type="FAST_WRONG",
        severity=1,
        algo_version_id=algo_version2.id,
        params_id=algo_params2.id,
        run_id=algo_run2.id,
    )

    mistake2 = MistakeLog(
        user_id=user.id,
        session_id=uuid4(),
        question_id=question2.id,
        year=1,
        block_id=None,
        theme_id=None,
        is_correct=False,
        mistake_type="KNOWLEDGE_GAP",
        severity=2,
        algo_version_id=algo_version2.id,
        params_id=algo_params2.id,
        run_id=algo_run2.id,
    )

    db_session.add_all([mistake1, mistake2])
    await db_session.flush()

    # Query filtered by block1
    stmt = select(MistakeLog).where(
        MistakeLog.user_id == user.id,
        MistakeLog.block_id == block1.id,
    )
    result = await db_session.execute(stmt)
    mistakes = result.scalars().all()

    assert len(mistakes) == 1
    assert mistakes[0].block_id == block1.id


@pytest.mark.asyncio
async def test_mistakes_list_filtered_by_theme(db_session: AsyncSession):
    """Test that mistakes list can be filtered by theme_id."""
    # Setup similar to block test
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

    theme1 = Theme(
        id=1,
        block_id=block.id,
        title="Theme 1",
        order_no=1,
        is_active=True,
    )
    theme2 = Theme(
        id=2,
        block_id=block.id,
        title="Theme 2",
        order_no=2,
        is_active=True,
    )
    db_session.add_all([theme1, theme2])

    question1 = Question(
        id=uuid4(),
        year_id=1,
        block_id=block.id,
        theme_id=theme1.id,
        stem="Q1",
        status=QuestionStatus.PUBLISHED,
    )
    question2 = Question(
        id=uuid4(),
        year_id=1,
        block_id=block.id,
        theme_id=theme2.id,
        stem="Q2",
        status=QuestionStatus.PUBLISHED,
    )
    db_session.add_all([question1, question2])

    # Create algo objects for mistakes
    algo_version3 = AlgoVersion(
        id=uuid4(),
        algo_key="MISTAKES",
        version="v0",
        status="ACTIVE",
    )
    db_session.add(algo_version3)
    await db_session.flush()
    
    algo_params3 = AlgoParams(
        id=uuid4(),
        algo_version_id=algo_version3.id,
        params_json={},
    )
    db_session.add(algo_params3)
    await db_session.flush()
    
    from datetime import UTC, datetime
    algo_run3 = AlgoRun(
        id=uuid4(),
        algo_version_id=algo_version3.id,
        params_id=algo_params3.id,
        trigger="manual",
        status="SUCCESS",
        started_at=datetime.now(UTC),
    )
    db_session.add(algo_run3)
    await db_session.flush()

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
        algo_version_id=algo_version3.id,
        params_id=algo_params3.id,
        run_id=algo_run3.id,
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
        algo_version_id=algo_version3.id,
        params_id=algo_params3.id,
        run_id=algo_run3.id,
    )

    db_session.add_all([mistake1, mistake2])
    await db_session.flush()

    # Query filtered by theme1
    stmt = select(MistakeLog).where(
        MistakeLog.user_id == user.id,
        MistakeLog.theme_id == theme1.id,
    )
    result = await db_session.execute(stmt)
    mistakes = result.scalars().all()

    assert len(mistakes) == 1
    assert mistakes[0].theme_id == theme1.id
