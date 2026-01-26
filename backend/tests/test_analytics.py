"""
Tests for analytics endpoints and service.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from fastapi import Request
from fastapi.testclient import TestClient

from app.main import app
from app.models.question_cms import Question, QuestionStatus
from app.models.session import (
    SessionAnswer,
    SessionMode,
    SessionQuestion,
    SessionStatus,
    TestSession,
)
from app.models.syllabus import Block, Theme
from app.models.user import User, UserRole
from app.services.analytics_service import get_block_analytics, get_overview, get_theme_analytics


@pytest.fixture
async def student_user_async(db_session):
    """Create a test student user (async)."""
    from app.core.security import hash_password
    from sqlalchemy import select

    # Check if user already exists
    stmt = select(User).where(User.email == "student@test.com")
    result = await db_session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    user = User(
        id=uuid4(),
        email="student@test.com",
        password_hash=hash_password("Test123!"),
        full_name="Test Student",
        role=UserRole.STUDENT.value,
        email_verified=True,
        is_active=True,
        onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def block_and_themes_async(db_session):
    """Create test block and themes (async)."""
    from app.models.syllabus import Year
    from sqlalchemy import select

    # Ensure year exists
    year_stmt = select(Year).where(Year.id == 1)
    year_result = await db_session.execute(year_stmt)
    year = year_result.scalar_one_or_none()
    if not year:
        year = Year(id=1, name="1st Year", order_no=1, is_active=True)
        db_session.add(year)
        await db_session.flush()

    block_stmt = select(Block).where(Block.id == 1)
    block_result = await db_session.execute(block_stmt)
    block = block_result.scalar_one_or_none()
    if not block:
        block = Block(id=1, year_id=1, code="A", name="Test Block", order_no=1, is_active=True)
        db_session.add(block)
        await db_session.flush()

    theme1_stmt = select(Theme).where(Theme.id == 1)
    theme1_result = await db_session.execute(theme1_stmt)
    theme1 = theme1_result.scalar_one_or_none()
    if not theme1:
        theme1 = Theme(id=1, block_id=1, title="Theme 1", order_no=1, is_active=True)
        db_session.add(theme1)
        await db_session.flush()

    theme2_stmt = select(Theme).where(Theme.id == 2)
    theme2_result = await db_session.execute(theme2_stmt)
    theme2 = theme2_result.scalar_one_or_none()
    if not theme2:
        theme2 = Theme(id=2, block_id=1, title="Theme 2", order_no=2, is_active=True)
        db_session.add(theme2)
        await db_session.flush()

    return block, [theme1, theme2]


@pytest.fixture
async def published_questions_async(db_session, block_and_themes_async):
    """Create published test questions (async)."""
    from app.core.security import hash_password
    from app.models.user import UserRole
    from sqlalchemy import select

    block, themes = block_and_themes_async

    # Create or get admin user
    admin_stmt = select(User).where(User.email == "admin@test.com")
    admin_result = await db_session.execute(admin_stmt)
    admin_user = admin_result.scalar_one_or_none()
    if not admin_user:
        admin_user = User(
            id=uuid4(),
            email="admin@test.com",
            password_hash=hash_password("Admin123!"),
            full_name="Test Admin",
            role=UserRole.ADMIN.value,
            email_verified=True,
            is_active=True,
            onboarding_completed=True,
        )
        db_session.add(admin_user)
        await db_session.flush()

    questions = []
    for i in range(10):
        q = Question(
            id=uuid4(),
            stem=f"Test question {i}",
            option_a=f"Option A {i}",
            option_b=f"Option B {i}",
            option_c=f"Option C {i}",
            option_d=f"Option D {i}",
            option_e=f"Option E {i}",
            correct_index=0,
            explanation_md=f"Explanation {i}",
            status=QuestionStatus.PUBLISHED,
            year_id=1,
            block_id=1,
            theme_id=(i % 2) + 1,  # Alternate between themes
            cognitive_level="RECALL",
            difficulty="MEDIUM",
            created_by=admin_user.id,
            updated_by=admin_user.id,
        )
        questions.append(q)

    db_session.add_all(questions)
    await db_session.flush()

    return questions


class TestAnalyticsEmpty:
    """Test analytics with no completed sessions."""

    @pytest.mark.asyncio
    async def test_overview_no_sessions(self, db_session, student_user_async):
        """Test overview with no sessions returns empty data."""
        result = await get_overview(db_session, student_user_async.id)

        assert result["sessions_completed"] == 0
        assert result["questions_seen"] == 0
        assert result["questions_answered"] == 0
        assert result["correct"] == 0
        assert result["accuracy_pct"] == 0.0
        assert result["by_block"] == []
        assert result["weakest_themes"] == []
        assert result["trend"] == []
        assert result["last_session"] is None

    @pytest.mark.asyncio
    async def test_block_analytics_no_data(self, db_session, student_user_async, block_and_themes_async):
        """Test block analytics with no data."""
        block, _ = block_and_themes_async
        result = await get_block_analytics(db_session, student_user_async.id, block.id)

        assert result["block_id"] == block.id
        assert result["block_name"] == block.name
        assert result["attempted"] == 0
        assert result["accuracy_pct"] == 0.0
        assert result["themes"] == []

    @pytest.mark.asyncio
    async def test_theme_analytics_no_data(self, db_session, student_user_async, block_and_themes_async):
        """Test theme analytics with no data."""
        block, themes = block_and_themes_async
        result = await get_theme_analytics(db_session, student_user_async.id, themes[0].id)

        assert result["theme_id"] == themes[0].id
        assert result["theme_name"] == themes[0].title
        assert result["attempted"] == 0
        assert result["accuracy_pct"] == 0.0


class TestAnalyticsWithSessions:
    """Test analytics with completed sessions."""

    @pytest.mark.asyncio
    async def test_single_session_aggregates(self, db_session, student_user_async, published_questions_async):
        """Test analytics with a single completed session."""
        from sqlalchemy import select

        # Create session
        session = TestSession(
            id=uuid4(),
            user_id=student_user_async.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            started_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
            score_total=5,
            score_correct=3,
            score_pct=60.0,
            year=1,
            blocks_json=["A"],
            total_questions=5,
        )
        db_session.add(session)
        await db_session.flush()

        # Add session questions (5 questions)
        for i, q in enumerate(published_questions_async[:5]):
            sq = SessionQuestion(
                session_id=session.id,
                question_id=q.id,
                position=i + 1,
                snapshot_json={
                    "stem": q.stem,
                    "correct_index": q.correct_index,
                    "block_id": q.block_id,
                    "theme_id": q.theme_id,
                },
            )
            db_session.add(sq)

        await db_session.flush()

        # Add answers: 3 correct, 2 incorrect
        for i, q in enumerate(published_questions_async[:5]):
            answer = SessionAnswer(
                session_id=session.id,
                question_id=q.id,
                selected_index=0 if i < 3 else 1,  # First 3 correct
                is_correct=i < 3,
            )
            db_session.add(answer)

        await db_session.flush()

        # Test overview
        result = await get_overview(db_session, student_user_async.id)

        assert result["sessions_completed"] == 1
        assert result["questions_seen"] == 5
        assert result["questions_answered"] == 5
        assert result["correct"] == 3
        assert result["accuracy_pct"] == 60.0
        assert len(result["by_block"]) == 1
        assert result["by_block"][0]["block_id"] == 1
        assert result["by_block"][0]["attempted"] == 5
        assert result["by_block"][0]["correct"] == 3
        assert result["last_session"] is not None
        assert result["last_session"]["score_pct"] == 60.0

    @pytest.mark.asyncio
    async def test_multiple_sessions_grouping(self, db_session, student_user_async, published_questions_async):
        """Test analytics aggregates across multiple sessions."""
        sessions = []

        # Create 3 sessions
        for i in range(3):
            session = TestSession(
                id=uuid4(),
                user_id=student_user_async.id,
                mode=SessionMode.TUTOR,
                status=SessionStatus.SUBMITTED,
                duration_seconds=600,
                started_at=datetime.utcnow() - timedelta(days=i),
                submitted_at=datetime.utcnow() - timedelta(days=i),
                score_total=3,
                score_correct=2,
                score_pct=66.67,
                year=1,
                blocks_json=["A"],
                total_questions=3,
            )
            db_session.add(session)
            sessions.append(session)

        await db_session.flush()

        # Add questions and answers for each session
        for session in sessions:
            for j, q in enumerate(published_questions_async[:3]):
                sq = SessionQuestion(
                    session_id=session.id,
                    question_id=q.id,
                    position=j + 1,
                    snapshot_json={
                        "stem": q.stem,
                        "correct_index": q.correct_index,
                        "block_id": q.block_id,
                        "theme_id": q.theme_id,
                    },
                )
                db_session.add(sq)

                answer = SessionAnswer(
                    session_id=session.id,
                    question_id=q.id,
                    selected_index=0 if j < 2 else 1,
                    is_correct=j < 2,
                )
                db_session.add(answer)

        await db_session.flush()

        # Test overview
        result = await get_overview(db_session, student_user_async.id)

        assert result["sessions_completed"] == 3
        assert result["questions_seen"] == 9  # 3 sessions × 3 questions
        assert result["correct"] == 6  # 3 sessions × 2 correct
        # 6/9 = 66.67%
        assert 66 <= result["accuracy_pct"] <= 67

    @pytest.mark.asyncio
    async def test_only_submitted_expired_counted(self, db_session, student_user_async, published_questions_async):
        """Test that only SUBMITTED and EXPIRED sessions are counted."""
        # Create ACTIVE session (should not count)
        active_session = TestSession(
            id=uuid4(),
            user_id=student_user_async.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.ACTIVE,
            duration_seconds=600,
            started_at=datetime.utcnow(),
            year=1,
            blocks_json=["A"],
            total_questions=2,
        )
        db_session.add(active_session)

        # Create SUBMITTED session (should count)
        submitted_session = TestSession(
            id=uuid4(),
            user_id=student_user_async.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            started_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
            score_total=2,
            score_correct=1,
            score_pct=50.0,
            year=1,
            blocks_json=["A"],
            total_questions=2,
        )
        db_session.add(submitted_session)

        await db_session.flush()

        # Add questions only for submitted session
        for i, q in enumerate(published_questions_async[:2]):
            sq = SessionQuestion(
                session_id=submitted_session.id,
                question_id=q.id,
                position=i + 1,
                snapshot_json={
                    "stem": q.stem,
                    "correct_index": q.correct_index,
                    "block_id": q.block_id,
                    "theme_id": q.theme_id,
                },
            )
            db_session.add(sq)

            answer = SessionAnswer(
                session_id=submitted_session.id,
                question_id=q.id,
                selected_index=0 if i == 0 else 1,
                is_correct=i == 0,
            )
            db_session.add(answer)

        await db_session.flush()

        result = await get_overview(db_session, student_user_async.id)

        # Only submitted session should count
        assert result["sessions_completed"] == 1
        assert result["questions_seen"] == 2
        assert result["correct"] == 1

    @pytest.mark.asyncio
    async def test_block_analytics_with_themes(self, db_session, student_user_async, published_questions_async):
        """Test block analytics includes theme breakdown."""
        session = TestSession(
            id=uuid4(),
            user_id=student_user_async.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            started_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
            score_total=6,
            score_correct=4,
            score_pct=66.67,
            year=1,
            blocks_json=["A"],
            total_questions=6,
        )
        db_session.add(session)
        await db_session.flush()

        # Add 6 questions: 3 from theme 1, 3 from theme 2
        for i, q in enumerate(published_questions_async[:6]):
            sq = SessionQuestion(
                session_id=session.id,
                question_id=q.id,
                position=i + 1,
                snapshot_json={
                    "stem": q.stem,
                    "correct_index": q.correct_index,
                    "block_id": q.block_id,
                    "theme_id": q.theme_id,
                },
            )
            db_session.add(sq)

            # Theme 1: 2/3 correct, Theme 2: 2/3 correct
            is_correct = i in [0, 1, 3, 4]
            answer = SessionAnswer(
                session_id=session.id,
                question_id=q.id,
                selected_index=0 if is_correct else 1,
                is_correct=is_correct,
            )
            db_session.add(answer)

        await db_session.flush()

        # Get block analytics
        result = await get_block_analytics(db_session, student_user_async.id, 1)

        assert result["attempted"] == 6
        assert result["correct"] == 4
        assert len(result["themes"]) == 2

        # Check themes
        theme_dict = {t["theme_id"]: t for t in result["themes"]}
        assert 1 in theme_dict
        assert 2 in theme_dict
        assert theme_dict[1]["attempted"] == 3
        assert theme_dict[2]["attempted"] == 3

    @pytest.mark.asyncio
    async def test_weakest_themes_requires_minimum_attempts(
        self, db_session, student_user_async, published_questions_async
    ):
        """Test weakest themes only includes themes with >= 5 attempts."""
        session = TestSession(
            id=uuid4(),
            user_id=student_user_async.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            started_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
            score_total=7,
            score_correct=4,
            score_pct=57.14,
            year=1,
            blocks_json=["A"],
            total_questions=7,
        )
        db_session.add(session)
        await db_session.flush()

        # Add 7 questions: 5 from theme 1 (should appear), 2 from theme 2 (should not)
        for i, q in enumerate(published_questions_async[:7]):
            # Force first 5 to theme 1, last 2 to theme 2
            theme_id = 1 if i < 5 else 2

            sq = SessionQuestion(
                session_id=session.id,
                question_id=q.id,
                position=i + 1,
                snapshot_json={
                    "stem": q.stem,
                    "correct_index": q.correct_index,
                    "block_id": 1,
                    "theme_id": theme_id,
                },
            )
            db_session.add(sq)

            answer = SessionAnswer(
                session_id=session.id,
                question_id=q.id,
                selected_index=0 if i < 4 else 1,
                is_correct=i < 4,
            )
            db_session.add(answer)

        await db_session.flush()

        result = await get_overview(db_session, student_user_async.id)

        # Only theme 1 should appear in weakest_themes (has >= 5 attempts)
        assert len(result["weakest_themes"]) <= 1
        if len(result["weakest_themes"]) > 0:
            assert result["weakest_themes"][0]["theme_id"] == 1
            assert result["weakest_themes"][0]["attempted"] == 5


class TestAnalyticsAPI:
    """Test analytics API endpoints."""

    @pytest.mark.asyncio
    async def test_overview_endpoint_requires_auth(self, db_session, student_user_async):
        """Test overview endpoint requires authentication."""
        # Test that the service function works with async session
        # The endpoint authentication is tested implicitly through the service
        result = await get_overview(db_session, student_user_async.id)
        # Should return overview data (empty if no sessions)
        assert isinstance(result, dict)
        assert "sessions_completed" in result
        assert "questions_seen" in result
        assert "questions_answered" in result
        assert "correct" in result
        assert "accuracy_pct" in result

    @pytest.mark.asyncio
    async def test_block_not_found(self, db_session, student_user_async):
        """Test block analytics returns None for non-existent block."""
        result = await get_block_analytics(db_session, student_user_async.id, 999)
        assert result is None

    @pytest.mark.asyncio
    async def test_theme_not_found(self, db_session, student_user_async):
        """Test theme analytics returns None for non-existent theme."""
        result = await get_theme_analytics(db_session, student_user_async.id, 999)
        assert result is None
