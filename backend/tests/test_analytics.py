"""
Tests for analytics endpoints and service.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

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
from app.services.analytics_service import get_overview, get_block_analytics, get_theme_analytics


@pytest.fixture
async def student_user(db):
    """Create a test student user."""
    user = User(
        id=uuid4(),
        email="student@test.com",
        hashed_password="hashed",
        full_name="Test Student",
        role=UserRole.STUDENT,
        year=1,
        is_email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def block_and_themes(db):
    """Create test block and themes."""
    block = Block(
        id=1,
        name="Test Block",
        order_index=1,
        year=1,
    )
    db.add(block)
    await db.commit()
    
    theme1 = Theme(
        id=1,
        block_id=1,
        title="Theme 1",
        order_index=1,
    )
    theme2 = Theme(
        id=2,
        block_id=1,
        title="Theme 2",
        order_index=2,
    )
    db.add_all([theme1, theme2])
    await db.commit()
    
    return block, [theme1, theme2]


@pytest.fixture
async def published_questions(db, block_and_themes):
    """Create published test questions."""
    block, themes = block_and_themes
    
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
            explanation=f"Explanation {i}",
            status=QuestionStatus.PUBLISHED,
            year=1,
            block_id=1,
            theme_id=(i % 2) + 1,  # Alternate between themes
            cognitive_level="RECALL",
            difficulty="MEDIUM",
            created_by_id=uuid4(),
        )
        questions.append(q)
    
    db.add_all(questions)
    await db.commit()
    
    return questions


class TestAnalyticsEmpty:
    """Test analytics with no completed sessions."""
    
    async def test_overview_no_sessions(self, db, student_user):
        """Test overview with no sessions returns empty data."""
        result = await get_overview(db, student_user.id)
        
        assert result["sessions_completed"] == 0
        assert result["questions_seen"] == 0
        assert result["questions_answered"] == 0
        assert result["correct"] == 0
        assert result["accuracy_pct"] == 0.0
        assert result["by_block"] == []
        assert result["weakest_themes"] == []
        assert result["trend"] == []
        assert result["last_session"] is None
    
    async def test_block_analytics_no_data(self, db, student_user, block_and_themes):
        """Test block analytics with no data."""
        block, _ = block_and_themes
        result = await get_block_analytics(db, student_user.id, block.id)
        
        assert result["block_id"] == block.id
        assert result["block_name"] == block.name
        assert result["attempted"] == 0
        assert result["accuracy_pct"] == 0.0
        assert result["themes"] == []
    
    async def test_theme_analytics_no_data(self, db, student_user, block_and_themes):
        """Test theme analytics with no data."""
        block, themes = block_and_themes
        result = await get_theme_analytics(db, student_user.id, themes[0].id)
        
        assert result["theme_id"] == themes[0].id
        assert result["theme_name"] == themes[0].title
        assert result["attempted"] == 0
        assert result["accuracy_pct"] == 0.0


class TestAnalyticsWithSessions:
    """Test analytics with completed sessions."""
    
    async def test_single_session_aggregates(self, db, student_user, published_questions):
        """Test analytics with a single completed session."""
        # Create session
        session = TestSession(
            id=uuid4(),
            user_id=student_user.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            created_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
            score_total=5,
            score_correct=3,
            score_pct=60.0,
        )
        db.add(session)
        await db.commit()
        
        # Add session questions (5 questions)
        for i, q in enumerate(published_questions[:5]):
            sq = SessionQuestion(
                id=uuid4(),
                session_id=session.id,
                question_id=q.id,
                position=i,
                snapshot_json={
                    "stem": q.stem,
                    "correct_index": q.correct_index,
                    "block_id": q.block_id,
                    "theme_id": q.theme_id,
                },
            )
            db.add(sq)
        
        await db.commit()
        
        # Add answers: 3 correct, 2 incorrect
        for i, q in enumerate(published_questions[:5]):
            answer = SessionAnswer(
                id=uuid4(),
                session_id=session.id,
                question_id=q.id,
                selected_index=0 if i < 3 else 1,  # First 3 correct
                is_correct=i < 3,
                answered_at=datetime.utcnow(),
            )
            db.add(answer)
        
        await db.commit()
        
        # Test overview
        result = await get_overview(db, student_user.id)
        
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
    
    async def test_multiple_sessions_grouping(self, db, student_user, published_questions):
        """Test analytics aggregates across multiple sessions."""
        sessions = []
        
        # Create 3 sessions
        for i in range(3):
            session = TestSession(
                id=uuid4(),
                user_id=student_user.id,
                mode=SessionMode.TUTOR,
                status=SessionStatus.SUBMITTED,
                duration_seconds=600,
                created_at=datetime.utcnow() - timedelta(days=i),
                submitted_at=datetime.utcnow() - timedelta(days=i),
                score_total=3,
                score_correct=2,
                score_pct=66.67,
            )
            db.add(session)
            sessions.append(session)
        
        await db.commit()
        
        # Add questions and answers for each session
        for session in sessions:
            for j, q in enumerate(published_questions[:3]):
                sq = SessionQuestion(
                    id=uuid4(),
                    session_id=session.id,
                    question_id=q.id,
                    position=j,
                    snapshot_json={
                        "stem": q.stem,
                        "correct_index": q.correct_index,
                        "block_id": q.block_id,
                        "theme_id": q.theme_id,
                    },
                )
                db.add(sq)
                
                answer = SessionAnswer(
                    id=uuid4(),
                    session_id=session.id,
                    question_id=q.id,
                    selected_index=0 if j < 2 else 1,
                    is_correct=j < 2,
                    answered_at=datetime.utcnow(),
                )
                db.add(answer)
        
        await db.commit()
        
        # Test overview
        result = await get_overview(db, student_user.id)
        
        assert result["sessions_completed"] == 3
        assert result["questions_seen"] == 9  # 3 sessions × 3 questions
        assert result["correct"] == 6  # 3 sessions × 2 correct
        # 6/9 = 66.67%
        assert 66 <= result["accuracy_pct"] <= 67
    
    async def test_only_submitted_expired_counted(self, db, student_user, published_questions):
        """Test that only SUBMITTED and EXPIRED sessions are counted."""
        # Create ACTIVE session (should not count)
        active_session = TestSession(
            id=uuid4(),
            user_id=student_user.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.ACTIVE,
            duration_seconds=600,
            created_at=datetime.utcnow(),
        )
        db.add(active_session)
        
        # Create SUBMITTED session (should count)
        submitted_session = TestSession(
            id=uuid4(),
            user_id=student_user.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            created_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
            score_total=2,
            score_correct=1,
            score_pct=50.0,
        )
        db.add(submitted_session)
        
        await db.commit()
        
        # Add questions only for submitted session
        for i, q in enumerate(published_questions[:2]):
            sq = SessionQuestion(
                id=uuid4(),
                session_id=submitted_session.id,
                question_id=q.id,
                position=i,
                snapshot_json={
                    "stem": q.stem,
                    "correct_index": q.correct_index,
                    "block_id": q.block_id,
                    "theme_id": q.theme_id,
                },
            )
            db.add(sq)
            
            answer = SessionAnswer(
                id=uuid4(),
                session_id=submitted_session.id,
                question_id=q.id,
                selected_index=0 if i == 0 else 1,
                is_correct=i == 0,
                answered_at=datetime.utcnow(),
            )
            db.add(answer)
        
        await db.commit()
        
        result = await get_overview(db, student_user.id)
        
        # Only submitted session should count
        assert result["sessions_completed"] == 1
        assert result["questions_seen"] == 2
        assert result["correct"] == 1
    
    async def test_block_analytics_with_themes(self, db, student_user, published_questions):
        """Test block analytics includes theme breakdown."""
        session = TestSession(
            id=uuid4(),
            user_id=student_user.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            created_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
            score_total=6,
            score_correct=4,
            score_pct=66.67,
        )
        db.add(session)
        await db.commit()
        
        # Add 6 questions: 3 from theme 1, 3 from theme 2
        for i, q in enumerate(published_questions[:6]):
            sq = SessionQuestion(
                id=uuid4(),
                session_id=session.id,
                question_id=q.id,
                position=i,
                snapshot_json={
                    "stem": q.stem,
                    "correct_index": q.correct_index,
                    "block_id": q.block_id,
                    "theme_id": q.theme_id,
                },
            )
            db.add(sq)
            
            # Theme 1: 2/3 correct, Theme 2: 2/3 correct
            is_correct = i in [0, 1, 3, 4]
            answer = SessionAnswer(
                id=uuid4(),
                session_id=session.id,
                question_id=q.id,
                selected_index=0 if is_correct else 1,
                is_correct=is_correct,
                answered_at=datetime.utcnow(),
            )
            db.add(answer)
        
        await db.commit()
        
        # Get block analytics
        result = await get_block_analytics(db, student_user.id, 1)
        
        assert result["attempted"] == 6
        assert result["correct"] == 4
        assert len(result["themes"]) == 2
        
        # Check themes
        theme_dict = {t["theme_id"]: t for t in result["themes"]}
        assert 1 in theme_dict
        assert 2 in theme_dict
        assert theme_dict[1]["attempted"] == 3
        assert theme_dict[2]["attempted"] == 3
    
    async def test_weakest_themes_requires_minimum_attempts(self, db, student_user, published_questions):
        """Test weakest themes only includes themes with >= 5 attempts."""
        session = TestSession(
            id=uuid4(),
            user_id=student_user.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            created_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
            score_total=7,
            score_correct=4,
            score_pct=57.14,
        )
        db.add(session)
        await db.commit()
        
        # Add 7 questions: 5 from theme 1 (should appear), 2 from theme 2 (should not)
        for i, q in enumerate(published_questions[:7]):
            # Force first 5 to theme 1, last 2 to theme 2
            theme_id = 1 if i < 5 else 2
            
            sq = SessionQuestion(
                id=uuid4(),
                session_id=session.id,
                question_id=q.id,
                position=i,
                snapshot_json={
                    "stem": q.stem,
                    "correct_index": q.correct_index,
                    "block_id": 1,
                    "theme_id": theme_id,
                },
            )
            db.add(sq)
            
            answer = SessionAnswer(
                id=uuid4(),
                session_id=session.id,
                question_id=q.id,
                selected_index=0 if i < 4 else 1,
                is_correct=i < 4,
                answered_at=datetime.utcnow(),
            )
            db.add(answer)
        
        await db.commit()
        
        result = await get_overview(db, student_user.id)
        
        # Only theme 1 should appear in weakest_themes (has >= 5 attempts)
        assert len(result["weakest_themes"]) <= 1
        if len(result["weakest_themes"]) > 0:
            assert result["weakest_themes"][0]["theme_id"] == 1
            assert result["weakest_themes"][0]["attempted"] == 5


class TestAnalyticsAPI:
    """Test analytics API endpoints."""
    
    async def test_overview_endpoint_requires_auth(self, client):
        """Test overview endpoint requires authentication."""
        response = await client.get("/v1/analytics/overview")
        assert response.status_code == 401
    
    async def test_block_not_found(self, db, student_user):
        """Test block analytics returns None for non-existent block."""
        result = await get_block_analytics(db, student_user.id, 999)
        assert result is None
    
    async def test_theme_not_found(self, db, student_user):
        """Test theme analytics returns None for non-existent theme."""
        result = await get_theme_analytics(db, student_user.id, 999)
        assert result is None
