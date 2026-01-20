"""
Tests for Mastery v0 algorithm.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.learning_engine.mastery.service import (
    collect_theme_attempts,
    compute_mastery_for_theme,
    compute_recency_weighted_accuracy,
    recompute_mastery_v0_for_user,
)
from app.models.learning_mastery import UserThemeMastery
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
from sqlalchemy import select


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


class TestRecencyWeighting:
    """Test recency-weighted accuracy computation."""
    
    def test_empty_attempts(self):
        """Test with no attempts."""
        params = {
            "recency_buckets": [
                {"days": 7, "weight": 0.50},
                {"days": 30, "weight": 0.30},
                {"days": 90, "weight": 0.20},
            ],
            "use_difficulty": False,
        }
        
        score, breakdown = compute_recency_weighted_accuracy([], params, datetime.utcnow())
        
        assert score == 0.0
        assert breakdown["reason"] == "no_attempts"
    
    def test_all_correct_recent(self):
        """Test with all correct recent attempts."""
        now = datetime.utcnow()
        attempts = [
            {"is_correct": True, "answered_at": now - timedelta(days=i), "difficulty": "medium"}
            for i in range(5)
        ]
        
        params = {
            "recency_buckets": [
                {"days": 7, "weight": 0.50},
                {"days": 30, "weight": 0.30},
                {"days": 90, "weight": 0.20},
            ],
            "use_difficulty": False,
        }
        
        score, breakdown = compute_recency_weighted_accuracy(attempts, params, now)
        
        # All correct = 1.0 accuracy in each bucket
        # 1.0 * 0.5 + 1.0 * 0.3 + 1.0 * 0.2 = 1.0
        assert score == 1.0
        assert breakdown["total_attempts"] == 5
    
    def test_recency_decay(self):
        """Test that recent attempts are weighted more."""
        now = datetime.utcnow()
        
        # 2 correct in last 7 days
        # 3 incorrect in 30-90 days
        attempts = [
            {"is_correct": True, "answered_at": now - timedelta(days=1), "difficulty": "medium"},
            {"is_correct": True, "answered_at": now - timedelta(days=3), "difficulty": "medium"},
            {"is_correct": False, "answered_at": now - timedelta(days=40), "difficulty": "medium"},
            {"is_correct": False, "answered_at": now - timedelta(days=50), "difficulty": "medium"},
            {"is_correct": False, "answered_at": now - timedelta(days=60), "difficulty": "medium"},
        ]
        
        params = {
            "recency_buckets": [
                {"days": 7, "weight": 0.50},
                {"days": 30, "weight": 0.30},
                {"days": 90, "weight": 0.20},
            ],
            "use_difficulty": False,
        }
        
        score, breakdown = compute_recency_weighted_accuracy(attempts, params, now)
        
        # 7d bucket: 2/2 = 1.0, contribution = 0.5
        # 30d bucket: 2/2 = 1.0, contribution = 0.3
        # 90d bucket: 2/5 = 0.4, contribution = 0.08
        # Total = 0.5 + 0.3 + 0.08 = 0.88
        assert score >= 0.85
        assert breakdown["buckets"]["7d"]["accuracy"] == 1.0
        assert breakdown["buckets"]["90d"]["accuracy"] == 0.4


class TestMasteryComputation:
    """Test full mastery computation for a theme."""
    
    async def test_no_sessions(self, db, student_user, block_and_themes):
        """Test with no completed sessions."""
        block, themes = block_and_themes
        
        attempts = await collect_theme_attempts(
            db, student_user.id, themes[0].id, 90, datetime.utcnow()
        )
        
        assert len(attempts) == 0
    
    async def test_collect_attempts_with_sessions(self, db, student_user, block_and_themes, published_questions):
        """Test collecting attempts from sessions."""
        block, themes = block_and_themes
        now = datetime.utcnow()
        
        # Create session with theme 1 questions
        session = TestSession(
            id=uuid4(),
            user_id=student_user.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            created_at=now - timedelta(days=1),
            submitted_at=now - timedelta(days=1),
            score_total=3,
            score_correct=2,
            score_pct=66.67,
        )
        db.add(session)
        await db.commit()
        
        # Add 3 questions from theme 1
        theme1_questions = [q for q in published_questions if q.theme_id == 1][:3]
        
        for i, q in enumerate(theme1_questions):
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
                    "year": q.year,
                    "difficulty": q.difficulty,
                },
            )
            db.add(sq)
            
            # 2 correct, 1 incorrect
            answer = SessionAnswer(
                id=uuid4(),
                session_id=session.id,
                question_id=q.id,
                selected_index=0 if i < 2 else 1,
                is_correct=i < 2,
                answered_at=now - timedelta(days=1),
            )
            db.add(answer)
        
        await db.commit()
        
        # Collect attempts
        attempts = await collect_theme_attempts(
            db, student_user.id, 1, 90, now
        )
        
        assert len(attempts) == 3
        assert sum(1 for a in attempts if a["is_correct"]) == 2
    
    async def test_min_attempts_threshold(self, db, student_user, block_and_themes):
        """Test that mastery is 0 when below min_attempts."""
        block, themes = block_and_themes
        
        params = {
            "lookback_days": 90,
            "min_attempts": 5,
            "recency_buckets": [{"days": 90, "weight": 1.0}],
            "use_difficulty": False,
        }
        
        # Only 2 attempts (below min of 5)
        result = await compute_mastery_for_theme(
            db, student_user.id, 1, block.id, themes[0].id, params, datetime.utcnow()
        )
        
        # Should have 0 attempts since no sessions exist
        assert result["attempts_total"] == 0
        assert result["mastery_score"] == 0.0
        assert "insufficient_attempts" in str(result["breakdown_json"])


class TestMasteryRecompute:
    """Test full recompute workflow."""
    
    async def test_recompute_creates_mastery_records(self, db, student_user, block_and_themes, published_questions):
        """Test that recompute creates mastery records."""
        block, themes = block_and_themes
        now = datetime.utcnow()
        
        # Create sessions across multiple themes
        for theme in themes:
            session = TestSession(
                id=uuid4(),
                user_id=student_user.id,
                mode=SessionMode.TUTOR,
                status=SessionStatus.SUBMITTED,
                duration_seconds=600,
                created_at=now - timedelta(days=5),
                submitted_at=now - timedelta(days=5),
                score_total=5,
                score_correct=4,
                score_pct=80.0,
            )
            db.add(session)
            await db.commit()
            
            # Add 5 questions from this theme
            theme_questions = [q for q in published_questions if q.theme_id == theme.id][:5]
            
            for i, q in enumerate(theme_questions):
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
                        "year": q.year,
                        "difficulty": q.difficulty,
                    },
                )
                db.add(sq)
                
                answer = SessionAnswer(
                    id=uuid4(),
                    session_id=session.id,
                    question_id=q.id,
                    selected_index=0 if i < 4 else 1,
                    is_correct=i < 4,
                    answered_at=now - timedelta(days=5),
                )
                db.add(answer)
            
            await db.commit()
        
        # Recompute mastery
        result = await recompute_mastery_v0_for_user(db, student_user.id)
        
        assert result["themes_computed"] == 2
        assert result["records_upserted"] == 2
        
        # Verify records in database
        stmt = select(UserThemeMastery).where(UserThemeMastery.user_id == student_user.id)
        mastery_result = await db.execute(stmt)
        mastery_records = mastery_result.scalars().all()
        
        assert len(mastery_records) == 2
        for record in mastery_records:
            assert record.attempts_total == 5
            assert record.correct_total == 4
            assert record.accuracy_pct == 80.0
            assert record.mastery_score > 0
            assert record.algo_version_id is not None
            assert record.params_id is not None
            assert record.run_id is not None
    
    async def test_recompute_upserts_existing_records(self, db, student_user, block_and_themes, published_questions):
        """Test that recompute updates existing mastery records."""
        block, themes = block_and_themes
        now = datetime.utcnow()
        
        # Create initial session
        session1 = TestSession(
            id=uuid4(),
            user_id=student_user.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            created_at=now - timedelta(days=10),
            submitted_at=now - timedelta(days=10),
            score_total=5,
            score_correct=3,
            score_pct=60.0,
        )
        db.add(session1)
        await db.commit()
        
        theme1_questions = [q for q in published_questions if q.theme_id == 1][:5]
        for i, q in enumerate(theme1_questions):
            sq = SessionQuestion(
                id=uuid4(),
                session_id=session1.id,
                question_id=q.id,
                position=i,
                snapshot_json={
                    "stem": q.stem,
                    "correct_index": q.correct_index,
                    "block_id": q.block_id,
                    "theme_id": q.theme_id,
                    "year": q.year,
                },
            )
            db.add(sq)
            
            answer = SessionAnswer(
                id=uuid4(),
                session_id=session1.id,
                question_id=q.id,
                selected_index=0 if i < 3 else 1,
                is_correct=i < 3,
                answered_at=now - timedelta(days=10),
            )
            db.add(answer)
        
        await db.commit()
        
        # First recompute
        result1 = await recompute_mastery_v0_for_user(db, student_user.id)
        assert result1["themes_computed"] == 1
        
        # Get initial mastery
        stmt = select(UserThemeMastery).where(
            UserThemeMastery.user_id == student_user.id,
            UserThemeMastery.theme_id == 1,
        )
        mastery_result = await db.execute(stmt)
        initial_mastery = mastery_result.scalar_one()
        initial_score = initial_mastery.mastery_score
        
        # Create new session with better performance
        session2 = TestSession(
            id=uuid4(),
            user_id=student_user.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            created_at=now - timedelta(days=1),
            submitted_at=now - timedelta(days=1),
            score_total=5,
            score_correct=5,
            score_pct=100.0,
        )
        db.add(session2)
        await db.commit()
        
        for i, q in enumerate(theme1_questions):
            sq = SessionQuestion(
                id=uuid4(),
                session_id=session2.id,
                question_id=q.id,
                position=i,
                snapshot_json={
                    "stem": q.stem,
                    "correct_index": q.correct_index,
                    "block_id": q.block_id,
                    "theme_id": q.theme_id,
                    "year": q.year,
                },
            )
            db.add(sq)
            
            answer = SessionAnswer(
                id=uuid4(),
                session_id=session2.id,
                question_id=q.id,
                selected_index=0,
                is_correct=True,
                answered_at=now - timedelta(days=1),
            )
            db.add(answer)
        
        await db.commit()
        
        # Second recompute
        result2 = await recompute_mastery_v0_for_user(db, student_user.id)
        assert result2["themes_computed"] == 1
        assert result2["records_upserted"] == 1
        
        # Get updated mastery
        mastery_result = await db.execute(stmt)
        updated_mastery = mastery_result.scalar_one()
        updated_score = updated_mastery.mastery_score
        
        # Mastery should improve (recent perfect session)
        assert updated_score > initial_score
        assert updated_mastery.attempts_total == 10
        assert updated_mastery.id == initial_mastery.id  # Same record, not new


class TestAlgoRunLogging:
    """Test that algo runs are logged correctly."""
    
    async def test_run_logging_on_success(self, db, student_user, block_and_themes, published_questions):
        """Test that successful recompute logs a run."""
        from app.models.learning import AlgoRun
        
        block, themes = block_and_themes
        now = datetime.utcnow()
        
        # Create minimal session
        session = TestSession(
            id=uuid4(),
            user_id=student_user.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.SUBMITTED,
            duration_seconds=600,
            created_at=now - timedelta(days=5),
            submitted_at=now - timedelta(days=5),
            score_total=5,
            score_correct=5,
            score_pct=100.0,
        )
        db.add(session)
        await db.commit()
        
        theme1_questions = [q for q in published_questions if q.theme_id == 1][:5]
        for i, q in enumerate(theme1_questions):
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
                    "year": q.year,
                },
            )
            db.add(sq)
            
            answer = SessionAnswer(
                id=uuid4(),
                session_id=session.id,
                question_id=q.id,
                selected_index=0,
                is_correct=True,
                answered_at=now - timedelta(days=5),
            )
            db.add(answer)
        
        await db.commit()
        
        # Recompute
        result = await recompute_mastery_v0_for_user(db, student_user.id)
        run_id = result["run_id"]
        
        # Verify run exists
        run = await db.get(AlgoRun, run_id)
        assert run is not None
        assert run.user_id == student_user.id
        assert run.status == "SUCCESS"
        assert run.completed_at is not None
        assert run.output_summary_json["themes_computed"] == 1
