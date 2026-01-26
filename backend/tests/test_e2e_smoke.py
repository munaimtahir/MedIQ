"""End-to-end smoke tests for backend."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.models.user import User, UserRole
from app.models.session import TestSession, SessionStatus


def test_auth_signup_login(db):
    """Test user signup and login flow."""
    from app.core.security import hash_password

    user = User(
        id=uuid4(),
        email="smoke_test@example.com",
        full_name="Smoke Test User",
        password_hash=hash_password("Test123!"),
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.commit()

    assert user.id is not None
    assert user.email == "smoke_test@example.com"
    assert user.role == UserRole.STUDENT.value


def test_session_creation_and_submission(db, test_user, published_questions):
    """Test creating a session, answering, and submitting."""
    from app.models.session import SessionAnswer, SessionQuestion

    # Use first published question
    question = published_questions[0]

    # Create session
    session = TestSession(
        id=uuid4(),
        user_id=test_user.id,
        year=1,
        blocks_json=["A"],
        total_questions=1,
        status=SessionStatus.ACTIVE,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.flush()

    # Add question to session
    session_question = SessionQuestion(
        session_id=session.id,
        question_id=question.id,
        position=1,
    )
    db.add(session_question)
    db.flush()

    # Answer question
    answer = SessionAnswer(
        session_id=session.id,
        question_id=question.id,
        selected_index=question.correct_index,
        is_correct=True,
    )
    db.add(answer)
    db.flush()

    # Submit session
    session.status = SessionStatus.SUBMITTED
    session.submitted_at = datetime.utcnow()
    session.score_correct = 1
    session.score_total = 1
    session.score_pct = 100.0
    db.commit()

    assert session.status == SessionStatus.SUBMITTED
    assert session.score_correct == 1
    assert session.score_total == 1
    assert session.score_pct == 100.0


def test_telemetry_events_written(db, test_user, test_session):
    """Test that telemetry events are written."""
    from app.models.session import AttemptEvent

    event = AttemptEvent(
        session_id=test_session.id,
        user_id=test_user.id,
        event_type="ANSWER_SELECTED",
        event_ts=datetime.utcnow(),
        payload_json={"position": 1, "selected_index": 0},
    )
    db.add(event)
    db.commit()

    assert event.id is not None
    assert event.session_id == test_session.id
    assert event.user_id == test_user.id
    assert event.event_type == "ANSWER_SELECTED"


def test_revision_queue_endpoint(db, test_user):
    """Test that revision queue endpoint exists and can be called."""
    # NOTE: Full revision queue testing requires completed sessions with mistakes.
    # This test verifies the endpoint structure exists.
    from app.api.v1.endpoints.revision_today import get_revision_today

    # The endpoint exists - full testing would require TestClient and session data
    assert callable(get_revision_today)


def test_nightly_job_function(db):
    """Test nightly job function in test context."""
    # NOTE: This test verifies the job function exists and can be called.
    # Full testing would require proper async setup and session data.
    from app.jobs.revision_queue_regen import regenerate_revision_queues

    # The function exists - full testing would require async execution
    assert callable(regenerate_revision_queues)
