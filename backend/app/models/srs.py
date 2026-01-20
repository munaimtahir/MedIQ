"""SRS (Spaced Repetition System) models using FSRS algorithm."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SRSUserParams(Base):
    """
    Per-user FSRS parameters and training metadata.

    Stores personalized FSRS weights learned from user's review history.
    Starts with global defaults and tunes as more data is collected.
    """

    __tablename__ = "srs_user_params"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    # FSRS configuration
    fsrs_version: Mapped[str] = mapped_column(String(20), nullable=False, default="fsrs-6")
    weights_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Personalized FSRS weights (19 params for v6)"
    )
    desired_retention: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.90, comment="Target retention probability"
    )

    # Training metadata
    n_review_logs: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Total review logs for this user"
    )
    last_trained_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last time weights were trained"
    )
    metrics_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Training metrics: logloss, brier, ece, val_size, etc.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_srs_user_params_last_trained", "last_trained_at"),
        Index("idx_srs_user_params_n_logs", "n_review_logs"),
    )


class SRSConceptState(Base):
    """
    Per-user per-concept memory state using FSRS.

    Tracks stability (S), difficulty (D), and due date for each concept.
    Updated after each review attempt.
    """

    __tablename__ = "srs_concept_state"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    # FSRS state variables
    stability: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Memory stability (days)"
    )
    difficulty: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Item difficulty [0, 10]"
    )

    # Scheduling
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Next review due date"
    )
    last_retrievability: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Retrievability at last review [0, 1]"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_srs_concept_state_user_due", "user_id", "due_at"),
        Index("idx_srs_concept_state_due_at", "due_at"),
        Index("idx_srs_concept_state_user_concept", "user_id", "concept_id"),
    )


class SRSReviewLog(Base):
    """
    Append-only log of all review attempts.

    Used for training personalized FSRS parameters and analytics.
    Each MCQ attempt is converted to a review log entry.
    """

    __tablename__ = "srs_review_log"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # References
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    concept_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Review data
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="FSRS rating 1-4 (Again, Hard, Good, Easy)"
    )
    correct: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="Whether answer was correct"
    )
    delta_days: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Days since last review"
    )

    # Telemetry (optional)
    time_spent_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Time spent on question (ms)"
    )
    change_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Number of answer changes"
    )

    # FSRS metrics
    predicted_retrievability: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Predicted retrievability at review time [0, 1]"
    )

    # Traceability
    raw_attempt_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, comment="Source session_answer.id"
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, comment="Source test_session.id"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("idx_srs_review_log_user_reviewed", "user_id", "reviewed_at"),
        Index("idx_srs_review_log_user_concept_reviewed", "user_id", "concept_id", "reviewed_at"),
        Index("idx_srs_review_log_session", "session_id"),
    )
