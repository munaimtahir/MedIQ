"""Test Session models for the test engine."""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class SessionMode(str, PyEnum):
    """Test session mode."""

    TUTOR = "TUTOR"
    EXAM = "EXAM"


class SessionStatus(str, PyEnum):
    """Test session status."""

    ACTIVE = "ACTIVE"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"


class TestSession(Base):
    """Test session - a single attempt at a test."""

    __tablename__ = "test_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False)

    # Session configuration
    mode = Column(
        Enum(SessionMode, name="session_mode", create_type=True),
        nullable=False,
        default=SessionMode.TUTOR,
    )
    status = Column(
        Enum(SessionStatus, name="session_status", create_type=True),
        nullable=False,
        default=SessionStatus.ACTIVE,
    )

    # Filter criteria used for question selection
    year = Column(Integer, nullable=False)
    blocks_json = Column(JSONB, nullable=False)  # ["A", "B", ...]
    themes_json = Column(JSONB, nullable=True)  # [theme_ids...] or null for all

    # Session metadata
    total_questions = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Timer configuration
    duration_seconds = Column(Integer, nullable=True)  # null = untimed
    expires_at = Column(DateTime(timezone=True), nullable=True)  # computed if duration set

    # Scoring (computed at submit)
    score_correct = Column(Integer, nullable=True)
    score_total = Column(Integer, nullable=True)
    score_pct = Column(Numeric(5, 2), nullable=True)  # 0.00 to 100.00

    # Algorithm snapshot (captured at session start for continuity)
    algo_profile_at_start = Column(String(50), nullable=False, server_default="V1_PRIMARY")  # "V1_PRIMARY" | "V0_FALLBACK"
    algo_overrides_at_start = Column(JSONB, nullable=False, server_default="{}")  # Per-module overrides at session start
    algo_policy_version_at_start = Column(String(50), nullable=True)  # Bridge policy version at session start

    # Exam mode snapshot (captured at session start - no mid-session effect)
    exam_mode_at_start = Column(Boolean, nullable=False, server_default="false")
    # Freeze-updates snapshot (captured at session start - no mid-session effect)
    freeze_updates_at_start = Column(Boolean, nullable=False, server_default="false")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    questions = relationship(
        "SessionQuestion", back_populates="session", cascade="all, delete-orphan"
    )
    answers = relationship("SessionAnswer", back_populates="session", cascade="all, delete-orphan")
    events = relationship("AttemptEvent", back_populates="session", cascade="all, delete-orphan")
    runtime_snapshot = relationship(
        "SessionRuntimeSnapshot",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_test_sessions_user_created", "user_id", "created_at"),
        Index("ix_test_sessions_status", "status"),
        Index("ix_test_sessions_expires_at", "expires_at"),
        Index("ix_test_sessions_algo_profile", "algo_profile_at_start"),
    )


class SessionQuestion(Base):
    """Questions included in a test session (frozen content)."""

    __tablename__ = "session_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("test_sessions.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    # Question reference
    position = Column(Integer, nullable=False)  # 1-based position in session
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", onupdate="CASCADE"),
        nullable=False,
    )

    # Freezing strategy: prefer version_id, fallback to snapshot
    question_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("question_versions.id", onupdate="CASCADE"),
        nullable=True,
    )
    snapshot_json = Column(
        JSONB, nullable=True
    )  # Fallback freeze: {stem, options, correct_index, explanation_md, ...}

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("TestSession", back_populates="questions")
    question = relationship("Question")
    question_version = relationship("QuestionVersion", foreign_keys=[question_version_id])

    __table_args__ = (
        UniqueConstraint("session_id", "position", name="uq_session_question_position"),
        UniqueConstraint("session_id", "question_id", name="uq_session_question_id"),
        Index("ix_session_questions_session_id", "session_id"),
    )


class SessionAnswer(Base):
    """Student answers for a test session."""

    __tablename__ = "session_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("test_sessions.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", onupdate="CASCADE"),
        nullable=False,
    )

    # Answer data
    selected_index = Column(SmallInteger, nullable=True)  # 0-4, null if not answered
    is_correct = Column(Boolean, nullable=True)  # Computed using frozen correct_index
    answered_at = Column(DateTime(timezone=True), nullable=True)
    changed_count = Column(Integer, nullable=False, default=0)  # Track answer changes
    marked_for_review = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    session = relationship("TestSession", back_populates="answers")
    question = relationship("Question")

    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_session_answer"),
        Index("ix_session_answers_session_id", "session_id"),
    )


class AttemptEvent(Base):
    """Telemetry events for test sessions (append-only log).

    IMPORTANT: This is an append-only table. Do NOT update or delete events.
    Events are stored for analytics and must remain immutable.
    """

    __tablename__ = "attempt_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event envelope fields
    event_version = Column(Integer, nullable=False, default=1)
    event_type = Column(String(100), nullable=False, index=True)
    event_ts = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    client_ts = Column(DateTime(timezone=True), nullable=True)  # Client-reported timestamp
    seq = Column(Integer, nullable=True)  # Client sequence number

    # Entity references
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("test_sessions.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False, index=True
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Metadata
    source = Column(String(50), nullable=True)  # "web", "mobile", "api"
    payload_json = Column(JSONB, nullable=False, server_default="{}")  # Event-specific data

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("TestSession", back_populates="events")

    __table_args__ = (
        Index("ix_attempt_events_session_ts", "session_id", "event_ts"),
        Index("ix_attempt_events_user_ts", "user_id", "event_ts"),
        Index("ix_attempt_events_type_ts", "event_type", "event_ts"),
        Index("ix_attempt_events_session_seq", "session_id", "seq"),
    )
