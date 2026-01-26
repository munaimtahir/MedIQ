"""Tests for telemetry functionality."""

import uuid
from datetime import datetime

import pytest

from app.models.question_cms import Question, QuestionStatus
from app.models.session import (
    AttemptEvent,
    SessionMode,
    SessionQuestion,
    SessionStatus,
    TestSession,
)
from app.models.user import User, UserRole
from app.schemas.telemetry import EventType


@pytest.fixture
def test_user(db):
    """Create a test user."""
    from app.core.security import hash_password
    
    user = User(
        id=uuid.uuid4(),
        email="telemetry@example.com",
        full_name="Telemetry User",
        role=UserRole.STUDENT.value,
        password_hash=hash_password("Test123!"),
        is_active=True,
        email_verified=True,
        onboarding_completed=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
async def test_session_async(db_session):
    """Create a test session (async)."""
    from app.core.security import hash_password
    from app.models.user import UserRole
    
    # Create test user first
    user = User(
        id=uuid.uuid4(),
        email="telemetry@example.com",
        full_name="Telemetry User",
        role=UserRole.STUDENT.value,
        password_hash=hash_password("Test123!"),
        is_active=True,
        email_verified=True,
        onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    session = TestSession(
        id=uuid.uuid4(),
        user_id=user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.ACTIVE,
        year=1,
        blocks_json=["A"],
        themes_json=None,
        total_questions=5,
        started_at=datetime.utcnow(),
    )
    db_session.add(session)
    await db_session.flush()
    return session, user


@pytest.fixture
def test_question(db):
    """Create a test question."""
    question = Question(
        id=uuid.uuid4(),
        status=QuestionStatus.PUBLISHED,
        year_id=1,
        block_id=1,
        theme_id=1,
        stem="Test question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        option_e="E",
        correct_index=0,
        explanation_md="Test",
        difficulty="MEDIUM",
        cognitive_level="UNDERSTAND",
    )
    db.add(question)
    db.flush()
    return question


@pytest.fixture
def session_with_question(db, test_session, test_question):
    """Add question to session."""
    session_q = SessionQuestion(
        session_id=test_session.id,
        position=1,
        question_id=test_question.id,
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
    return test_session, test_question


def test_event_storage_with_envelope_fields(db, test_user, test_session, test_question):
    """Test that events are stored with all envelope fields."""
    # Create event with all envelope fields
    event = AttemptEvent(
        session_id=test_session.id,
        user_id=test_user.id,
        event_type=EventType.QUESTION_VIEWED.value,
        event_version=1,
        event_ts=datetime.utcnow(),
        client_ts=datetime.utcnow(),
        seq=1,
        question_id=test_question.id,
        source="web",
        payload_json={"position": 1},
    )
    db.add(event)
    db.flush()

    # Verify all fields stored
    assert event.id is not None
    assert event.event_version == 1
    assert event.event_type == EventType.QUESTION_VIEWED.value
    assert event.event_ts is not None
    assert event.client_ts is not None
    assert event.seq == 1
    assert event.session_id == test_session.id
    assert event.user_id == test_user.id
    assert event.question_id == test_question.id
    assert event.source == "web"
    assert event.payload_json == {"position": 1}


def test_append_only_behavior(db, test_user, test_session):
    """Test that events are append-only (verify at application level)."""
    # Create event
    event = AttemptEvent(
        session_id=test_session.id,
        user_id=test_user.id,
        event_type=EventType.SESSION_CREATED.value,
        event_ts=datetime.utcnow(),
        payload_json={"mode": "TUTOR"},
    )
    db.add(event)
    db.flush()

    original_payload = event.payload_json.copy()

    # Attempt to modify (should be avoided in application code)
    # This test documents that we DON'T update events
    # In real application, there should be no update/delete endpoints

    # Verify event unchanged
    db.refresh(event)
    assert event.payload_json == original_payload


def test_event_with_minimal_fields(db, test_user, test_session):
    """Test that events can be created with minimal required fields."""
    event = AttemptEvent(
        session_id=test_session.id,
        user_id=test_user.id,
        event_type=EventType.SESSION_SUBMITTED.value,
        event_ts=datetime.utcnow(),
        payload_json={},
    )
    db.add(event)
    db.flush()

    assert event.id is not None
    assert event.client_ts is None
    assert event.seq is None
    assert event.question_id is None
    assert event.source is None


def test_event_types_validation(db, test_user, test_session):
    """Test that all event types can be stored."""
    event_types = [
        EventType.SESSION_CREATED,
        EventType.QUESTION_VIEWED,
        EventType.NAVIGATE_NEXT,
        EventType.NAVIGATE_PREV,
        EventType.NAVIGATE_JUMP,
        EventType.ANSWER_SELECTED,
        EventType.ANSWER_CHANGED,
        EventType.MARK_FOR_REVIEW_TOGGLED,
        EventType.SESSION_SUBMITTED,
        EventType.SESSION_EXPIRED,
        EventType.REVIEW_OPENED,
        EventType.PAUSE_BLUR,
    ]

    for event_type in event_types:
        event = AttemptEvent(
            session_id=test_session.id,
            user_id=test_user.id,
            event_type=event_type.value,
            event_ts=datetime.utcnow(),
            payload_json={},
        )
        db.add(event)

    db.flush()

    # Verify all events stored
    events_count = db.query(AttemptEvent).filter(AttemptEvent.session_id == test_session.id).count()
    assert events_count == len(event_types)


@pytest.mark.asyncio
async def test_telemetry_service_best_effort(db_session, test_session_async):
    """Test that telemetry service handles failures gracefully."""
    from app.services.telemetry import log_event

    session, user = test_session_async
    
    # Valid event should succeed
    event = await log_event(
        db_session,
        session_id=session.id,
        user_id=user.id,
        event_type=EventType.QUESTION_VIEWED,
        payload={"position": 1},
    )

    assert event is not None
    assert event.event_type == EventType.QUESTION_VIEWED.value
    await db_session.flush()


def test_payload_size_limit_enforced():
    """Test that payload size validation works (in Pydantic schema)."""
    from app.schemas.telemetry import TelemetryEventSubmit

    # Small payload should pass
    small_event = TelemetryEventSubmit(
        event_type=EventType.QUESTION_VIEWED,
        session_id=uuid.uuid4(),
        payload={"position": 1},
    )
    assert small_event.payload == {"position": 1}

    # Large payload should fail validation
    large_payload = {"data": "x" * 5000}  # > 4KB
    with pytest.raises(ValueError):
        TelemetryEventSubmit(
            event_type=EventType.QUESTION_VIEWED,
            session_id=uuid.uuid4(),
            payload=large_payload,
        )


def test_batch_size_limit_enforced():
    """Test that batch size validation works."""
    from app.schemas.telemetry import TelemetryBatchSubmit, TelemetryEventSubmit

    # Small batch should pass
    events = [
        TelemetryEventSubmit(
            event_type=EventType.QUESTION_VIEWED,
            session_id=uuid.uuid4(),
            payload={"position": i},
        )
        for i in range(10)
    ]
    batch = TelemetryBatchSubmit(source="web", events=events)
    assert len(batch.events) == 10

    # Large batch should fail validation
    large_events = [
        TelemetryEventSubmit(
            event_type=EventType.QUESTION_VIEWED,
            session_id=uuid.uuid4(),
            payload={"position": i},
        )
        for i in range(51)
    ]
    with pytest.raises(ValueError):
        TelemetryBatchSubmit(source="web", events=large_events)
