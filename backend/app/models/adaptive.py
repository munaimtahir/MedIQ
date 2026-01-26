"""
SQLAlchemy models for adaptive selection v1 (Constrained Multi-Armed Bandit).

Implements Thompson Sampling over theme arms with constraints.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BanditUserThemeState(Base):
    """
    Per-user per-theme Beta posterior for Thompson Sampling.

    Tracks learning yield estimates for each (user, theme) pair.
    Updated after session completion using BKT mastery delta as reward.
    """

    __tablename__ = "bandit_user_theme_state"

    # Composite primary key
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    theme_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("themes.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Beta posterior parameters (initialized to Beta(1,1) = Uniform)
    a: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0, comment="Beta alpha (success count + prior)"
    )
    b: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0, comment="Beta beta (failure count + prior)"
    )

    # Tracking
    n_sessions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Number of sessions this theme was selected"
    )
    last_selected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_reward: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Reward from most recent session [0,1]"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_bandit_user_theme_state_user_last_selected", "user_id", "last_selected_at"),
    )


class AdaptiveSelectionLog(Base):
    """
    Append-only log of adaptive selection requests.

    Records full diagnostic information for debugging, evaluation, and auditing.
    Each row represents one call to the adaptive selection endpoint.
    """

    __tablename__ = "adaptive_selection_log"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User and timing
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    # Request parameters
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="tutor, exam, revision"
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="mixed, revision, weakness"
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    block_ids: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="List of block IDs requested"
    )
    theme_ids_filter: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Optional theme filter"
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Determinism / reproducibility
    seed: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Deterministic seed for RNG"
    )

    # Algo provenance
    algo_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("algo_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    params_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("algo_params.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    # Diagnostic data (stored as JSON for flexibility)
    candidates_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Candidate themes: base_priority, sampled_y, final_score, supply, etc.",
    )
    selected_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="Selected themes with quotas"
    )
    question_ids_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="Final ordered question IDs"
    )
    stats_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Stats: due_ratio, avg_p_pred, difficulty_distribution, exclusions",
    )

    __table_args__ = (
        Index("idx_adaptive_selection_log_user_requested", "user_id", "requested_at"),
        Index("idx_adaptive_selection_log_run_id", "run_id"),
    )
