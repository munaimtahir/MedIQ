"""
SQLAlchemy models for difficulty rating system (Elo v1).

Tracks user ability and question difficulty with uncertainty-aware dynamic K.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RatingScope(str, Enum):
    """Scope for difficulty ratings (global or theme-specific)."""

    GLOBAL = "GLOBAL"
    THEME = "THEME"


class DifficultyUserRating(Base):
    """
    User ability rating (θ) with uncertainty.

    Supports both global and theme-scoped ratings for hierarchical modeling.
    """

    __tablename__ = "difficulty_user_rating"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)  # GLOBAL or THEME
    scope_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, comment="NULL for GLOBAL; theme_id for THEME"
    )

    # Elo rating components
    rating: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, comment="User ability (θ)"
    )
    uncertainty: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Rating deviation (RD-like)"
    )

    # Tracking
    n_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
        Index(
            "idx_difficulty_user_rating_lookup", "user_id", "scope_type", "scope_id", unique=True
        ),
        Index("idx_difficulty_user_rating_activity", "user_id", "scope_type", "last_seen_at"),
    )


class DifficultyQuestionRating(Base):
    """
    Question difficulty rating (b) with uncertainty.

    Supports both global and theme-scoped ratings.
    """

    __tablename__ = "difficulty_question_rating"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    question_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, comment="NULL for GLOBAL; theme_id for THEME"
    )

    # Elo rating components
    rating: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, comment="Question difficulty (b)"
    )
    uncertainty: Mapped[float] = mapped_column(Float, nullable=False, comment="Rating deviation")

    # Tracking
    n_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
        Index(
            "idx_difficulty_question_rating_lookup",
            "question_id",
            "scope_type",
            "scope_id",
            unique=True,
        ),
        Index("idx_difficulty_question_rating_distribution", "scope_type", "rating"),
    )


class DifficultyUpdateLog(Base):
    """
    Append-only log of difficulty rating updates.

    Records every update for audit, offline evaluation, and calibration metrics.
    Captures pre/post snapshots and dynamic K values used.
    """

    __tablename__ = "difficulty_update_log"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Attempt context
    attempt_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True
    )
    theme_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    # What was updated
    scope_used: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="GLOBAL, THEME, or BOTH"
    )

    # Observation
    score: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="Correct (true) or incorrect (false)"
    )
    p_pred: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Predicted probability of correct"
    )

    # User rating snapshot (global)
    user_rating_pre: Mapped[float] = mapped_column(Float, nullable=False)
    user_rating_post: Mapped[float] = mapped_column(Float, nullable=False)
    user_unc_pre: Mapped[float] = mapped_column(Float, nullable=False)
    user_unc_post: Mapped[float] = mapped_column(Float, nullable=False)

    # Question rating snapshot (global)
    q_rating_pre: Mapped[float] = mapped_column(Float, nullable=False)
    q_rating_post: Mapped[float] = mapped_column(Float, nullable=False)
    q_unc_pre: Mapped[float] = mapped_column(Float, nullable=False)
    q_unc_post: Mapped[float] = mapped_column(Float, nullable=False)

    # Dynamic K values used
    k_u_used: Mapped[float] = mapped_column(Float, nullable=False, comment="User K value applied")
    k_q_used: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Question K value applied"
    )

    # Model parameters used
    guess_floor_used: Mapped[float] = mapped_column(Float, nullable=False)
    scale_used: Mapped[float] = mapped_column(Float, nullable=False)

    # Algo provenance
    algo_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("algo_versions.id", ondelete="SET NULL"), nullable=True
    )
    params_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("algo_params.id", ondelete="SET NULL"), nullable=True
    )
    run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("algo_runs.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("idx_difficulty_update_log_user", "user_id", "created_at"),
        Index("idx_difficulty_update_log_question", "question_id", "created_at"),
        Index("idx_difficulty_update_log_theme", "theme_id", "created_at"),
        Index("idx_difficulty_update_log_attempt", "attempt_id", unique=True),
    )
