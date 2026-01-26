"""BKT (Bayesian Knowledge Tracing) models."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BKTSkillParams(Base):
    """
    BKT parameters per concept (skill).

    Stores the 4-parameter BKT model: L0, T, S, G
    - L0: Prior probability of mastery
    - T: Probability of learning (transition)
    - S: Probability of slip (learned but answers wrong)
    - G: Probability of guess (unlearned but answers correct)
    """

    __tablename__ = "bkt_skill_params"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    concept_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    algo_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("algo_versions.id", ondelete="CASCADE"), nullable=False
    )

    # BKT 4-parameter model
    p_L0: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Prior probability of mastery"
    )
    p_T: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Probability of learning (transition)"
    )
    p_S: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Probability of slip (learned but wrong)"
    )
    p_G: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Probability of guess (unlearned but correct)"
    )

    # Metadata
    constraints_applied: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    fitted_on_data_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fitted_on_data_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metrics: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, comment="AUC, RMSE, logloss, CV metrics"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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
        Index("idx_bkt_skill_params_concept_active", "concept_id", "is_active"),
        Index("idx_bkt_skill_params_algo_version", "algo_version_id"),
        Index("idx_bkt_skill_params_fitted_at", "fitted_at"),
    )


class BKTUserSkillState(Base):
    """
    Per-user per-concept mastery state.

    Tracks the current mastery probability and attempt history for each user-concept pair.
    Updated online after each attempt.
    """

    __tablename__ = "bkt_user_skill_state"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    p_mastery: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, comment="Current mastery probability"
    )
    n_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_question_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    algo_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("algo_versions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Version used for last update",
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
        Index("idx_bkt_user_skill_state_user", "user_id"),
        Index("idx_bkt_user_skill_state_concept", "concept_id"),
        Index("idx_bkt_user_skill_state_mastery", "p_mastery"),
        Index("idx_bkt_user_skill_state_last_attempt", "last_attempt_at"),
    )


class MasterySnapshot(Base):
    """
    Historical snapshots of mastery for analytics.

    Allows time-series analysis without recomputing from raw attempts.
    """

    __tablename__ = "mastery_snapshot"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    concept_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    p_mastery: Mapped[float] = mapped_column(Float, nullable=False)
    n_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    algo_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("algo_versions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("idx_mastery_snapshot_user_concept", "user_id", "concept_id"),
        Index("idx_mastery_snapshot_created_at", "created_at"),
        Index("idx_mastery_snapshot_concept", "concept_id"),
    )
