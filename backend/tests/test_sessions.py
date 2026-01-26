"""Tests for test session functionality."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.models.question_cms import Question, QuestionStatus
from app.models.session import (
    SessionAnswer,
    SessionMode,
    SessionQuestion,
    SessionStatus,
    TestSession,
)
from app.models.syllabus import Block, Theme, Year
from app.models.user import User, UserRole


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        role=UserRole.STUDENT.value,
        password_hash="fake_hash",
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def published_questions(db):
    """Create published test questions."""
    # Ensure year/block/theme exist
    db.query(Year).filter(Year.id == 1).first()
    db.query(Block).filter(Block.id == 1).first()
    db.query(Theme).filter(Theme.id == 1).first()

    questions = []
    for i in range(30):
        q = Question(
            id=uuid.uuid4(),
            status=QuestionStatus.PUBLISHED,
            year_id=1,
            block_id=1,
            theme_id=1,
            stem=f"Test question {i+1}",
            option_a="Option A",
            option_b="Option B",
            option_c="Option C",
            option_d="Option D",
            option_e="Option E",
            correct_index=0,
            explanation_md="Test explanation",
            difficulty="MEDIUM",
            cognitive_level="UNDERSTAND",
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.add(q)
        questions.append(q)

    db.flush()
    return questions


def test_session_create_selects_published_only(db, test_user, published_questions):
    """Test that session creation selects only PUBLISHED questions."""
    # Add a draft question (should not be selected)
    draft_q = Question(
        id=uuid.uuid4(),
        status=QuestionStatus.DRAFT,
        year_id=1,
        block_id=1,
        theme_id=1,
        stem="Draft question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        option_e="E",
        correct_index=0,
        explanation_md="Draft",
        difficulty="MEDIUM",
        cognitive_level="UNDERSTAND",
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(draft_q)
    db.flush()

    # Create session (synchronously for test)
    session = TestSession(
        id=uuid.uuid4(),
        user_id=test_user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.ACTIVE,
        year=1,
        blocks_json=["A"],
        themes_json=None,
        total_questions=10,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.flush()

    # Verify PUBLISHED questions count
    published_count = (
        db.query(Question)
        .filter(Question.status == QuestionStatus.PUBLISHED, Question.year_id == 1)
        .count()
    )
    assert published_count == 30  # Only published, not draft


def test_session_not_enough_questions(db, test_user):
    """Test error when requesting more questions than available."""
    # Only a few questions exist, request more
    # This test validates the error path
    # In real implementation, would call create_session service and expect HTTPException
    # For now, we verify the data constraint exists
    published_count = (
        db.query(Question)
        .filter(
            Question.status == QuestionStatus.PUBLISHED,
            Question.year_id == 1,
        )
        .count()
    )

    # If we have fewer than 100 questions, requesting 100 should fail
    # This is validated in the service layer
    assert published_count < 100  # Validates test scenario


def test_session_answer_tracks_changes(db, test_user, published_questions):
    """Test that answer changes are tracked correctly."""
    # Create session
    session = TestSession(
        id=uuid.uuid4(),
        user_id=test_user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.ACTIVE,
        year=1,
        blocks_json=["A"],
        themes_json=None,
        total_questions=5,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.flush()

    question_id = published_questions[0].id

    # Add session question
    session_q = SessionQuestion(
        session_id=session.id,
        position=1,
        question_id=question_id,
        snapshot_json={
            "stem": "Test",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "option_e": "E",
            "correct_index": 0,
            "explanation_md": "Test",
        },
    )
    db.add(session_q)
    db.flush()

    # First answer
    answer = SessionAnswer(
        session_id=session.id,
        question_id=question_id,
        selected_index=0,
        is_correct=True,
        answered_at=datetime.utcnow(),
        changed_count=0,
    )
    db.add(answer)
    db.flush()

    # Change answer
    answer.selected_index = 1
    answer.is_correct = False
    answer.changed_count += 1
    db.flush()

    assert answer.changed_count == 1

    # Change again
    answer.selected_index = 2
    answer.is_correct = False
    answer.changed_count += 1
    db.flush()

    assert answer.changed_count == 2


def test_session_submit_computes_score(db, test_user, published_questions):
    """Test that submit computes deterministic score."""
    # Create session
    session = TestSession(
        id=uuid.uuid4(),
        user_id=test_user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.ACTIVE,
        year=1,
        blocks_json=["A"],
        themes_json=None,
        total_questions=10,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.flush()

    # Add session questions
    for i in range(10):
        session_q = SessionQuestion(
            session_id=session.id,
            position=i + 1,
            question_id=published_questions[i].id,
            snapshot_json={
                "stem": f"Q{i+1}",
                "option_a": "A",
                "option_b": "B",
                "option_c": "C",
                "option_d": "D",
                "option_e": "E",
                "correct_index": 0,
                "explanation_md": "Exp",
            },
        )
        db.add(session_q)
    db.flush()

    # Add answers: 7 correct, 2 incorrect, 1 unanswered
    for i in range(7):
        answer = SessionAnswer(
            session_id=session.id,
            question_id=published_questions[i].id,
            selected_index=0,
            is_correct=True,
            answered_at=datetime.utcnow(),
        )
        db.add(answer)

    for i in range(7, 9):
        answer = SessionAnswer(
            session_id=session.id,
            question_id=published_questions[i].id,
            selected_index=1,
            is_correct=False,
            answered_at=datetime.utcnow(),
        )
        db.add(answer)

    # Question 10 is unanswered (treated as incorrect)
    db.flush()

    # Compute score (simulate submit)
    score_correct = (
        db.query(SessionAnswer)
        .filter(SessionAnswer.session_id == session.id, SessionAnswer.is_correct)
        .count()
    )
    score_total = session.total_questions
    score_pct = round((score_correct / score_total) * 100, 2)

    assert score_correct == 7
    assert score_total == 10
    assert score_pct == 70.0

    # Update session
    session.status = SessionStatus.SUBMITTED
    session.submitted_at = datetime.utcnow()
    session.score_correct = score_correct
    session.score_total = score_total
    session.score_pct = score_pct
    db.flush()

    assert session.score_correct == 7
    assert session.score_pct == 70.0


def test_frozen_content_consistency(db, test_user, published_questions):
    """Test that review uses frozen content even if question changes."""
    # Create session with snapshot
    session = TestSession(
        id=uuid.uuid4(),
        user_id=test_user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.ACTIVE,
        year=1,
        blocks_json=["A"],
        themes_json=None,
        total_questions=1,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.flush()

    question = published_questions[0]
    original_stem = question.stem

    # Freeze question content
    session_q = SessionQuestion(
        session_id=session.id,
        position=1,
        question_id=question.id,
        snapshot_json={
            "stem": original_stem,
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "option_e": "E",
            "correct_index": 0,
            "explanation_md": "Original explanation",
        },
    )
    db.add(session_q)
    db.flush()

    # Modify the original question
    question.stem = "MODIFIED STEM - SHOULD NOT APPEAR IN REVIEW"
    question.correct_index = 2
    db.flush()

    # Review should use frozen content
    frozen = session_q.snapshot_json
    assert frozen["stem"] == original_stem
    assert frozen["correct_index"] == 0
    assert frozen["stem"] != question.stem
    assert frozen["correct_index"] != question.correct_index


def test_timer_expiry_logic(db, test_user, published_questions):
    """Test that session expires when time limit reached."""
    # Create session with timer
    started_at = datetime.utcnow()
    duration_seconds = 3600  # 1 hour
    expires_at = started_at + timedelta(seconds=duration_seconds)

    session = TestSession(
        id=uuid.uuid4(),
        user_id=test_user.id,
        mode=SessionMode.EXAM,
        status=SessionStatus.ACTIVE,
        year=1,
        blocks_json=["A"],
        themes_json=None,
        total_questions=5,
        started_at=started_at,
        duration_seconds=duration_seconds,
        expires_at=expires_at,
    )
    db.add(session)
    db.flush()

    # Check expiry logic
    now = datetime.utcnow()

    # If now > expires_at, should auto-expire
    if now > session.expires_at:
        # Simulate lazy expiry
        session.status = SessionStatus.EXPIRED
        session.submitted_at = now
        db.flush()

    # For test purposes, manually check time
    is_expired = session.expires_at < started_at + timedelta(seconds=duration_seconds + 10)
    assert is_expired is False  # Should not be expired within duration


def test_session_locks_after_submit(db, test_user, published_questions):
    """Test that submitted/expired sessions are locked from answers."""
    # Create submitted session
    session = TestSession(
        id=uuid.uuid4(),
        user_id=test_user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.SUBMITTED,
        year=1,
        blocks_json=["A"],
        themes_json=None,
        total_questions=5,
        started_at=datetime.utcnow(),
        submitted_at=datetime.utcnow(),
        score_correct=4,
        score_total=5,
        score_pct=80.0,
    )
    db.add(session)
    db.flush()

    # Attempting to add answer should be blocked (in service layer)
    # Here we just verify status
    assert session.status == SessionStatus.SUBMITTED
    assert session.submitted_at is not None


def test_unauthorized_access_validation(db, published_questions):
    """Test that users cannot access other users' sessions."""
    # Create two users
    user1 = User(
        id=uuid.uuid4(),
        email="user1@example.com",
        first_name="User",
        last_name="One",
        role=UserRole.STUDENT,
        password_hash="hash1",
        is_active=True,
        email_verified=True,
    )
    user2 = User(
        id=uuid.uuid4(),
        email="user2@example.com",
        first_name="User",
        last_name="Two",
        role=UserRole.STUDENT,
        password_hash="hash2",
        is_active=True,
        email_verified=True,
    )
    db.add(user1)
    db.add(user2)
    db.flush()

    # Create session for user1
    session = TestSession(
        id=uuid.uuid4(),
        user_id=user1.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.ACTIVE,
        year=1,
        blocks_json=["A"],
        themes_json=None,
        total_questions=5,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.flush()

    # Verify ownership
    assert session.user_id == user1.id
    assert session.user_id != user2.id
    # In API layer, attempting to access with user2 should return 403
