"""Rank prediction v1 (quantile-based) subsystem database models.

Shadow/offline prediction only. Never used for student-facing decisions
unless FEATURE_RANK_ACTIVE is enabled and runtime override allows it.
"""

import uuid
from enum import Enum

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class RankSnapshotStatus(str, Enum):
    """Rank snapshot status."""

    OK = "ok"
    INSUFFICIENT_DATA = "insufficient_data"
    UNSTABLE = "unstable"
    BLOCKED_FROZEN = "blocked_frozen"
    DISABLED = "disabled"


class RankRunStatus(str, Enum):
    """Rank model run status."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    BLOCKED_FROZEN = "BLOCKED_FROZEN"
    DISABLED = "DISABLED"


class RankPredictionSnapshot(Base):
    """Rank prediction snapshot per user/cohort (daily bucket)."""

    __tablename__ = "rank_prediction_snapshot"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    cohort_key = Column(String(100), nullable=False)  # e.g., "year:1", "year:2:block:A"
    theta_proxy = Column(Float, nullable=True)  # ability proxy used
    predicted_percentile = Column(Float, nullable=True)  # 0..1
    band_low = Column(Float, nullable=True)
    band_high = Column(Float, nullable=True)
    status = Column(
        ENUM(RankSnapshotStatus, name="rank_snapshot_status", create_type=False),
        nullable=False,
        server_default="ok",
    )
    model_version = Column(String(50), nullable=False, server_default="rank_v1_empirical_cdf")
    features_hash = Column(String(64), nullable=True)  # Hash of features used
    computed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index(
            "uq_rank_snapshot_user_cohort_model_date",
            "user_id",
            "cohort_key",
            "model_version",
            sa.func.date(computed_at),
            unique=True,
        ),
        Index("ix_rank_snapshot_user_id", "user_id"),
        Index("ix_rank_snapshot_cohort_key", "cohort_key"),
        Index("ix_rank_snapshot_computed_at", "computed_at"),
        Index("ix_rank_snapshot_status", "status"),
    )


class RankModelRun(Base):
    """Rank model evaluation run (shadow evaluation registry)."""

    __tablename__ = "rank_model_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cohort_key = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False, server_default="rank_v1_empirical_cdf")
    dataset_spec = Column(JSONB, nullable=False, server_default="{}")
    metrics = Column(JSONB, nullable=True)
    status = Column(
        ENUM(RankRunStatus, name="rank_run_status", create_type=False),
        nullable=False,
        server_default="QUEUED",
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        Index("ix_rank_model_run_cohort_key", "cohort_key"),
        Index("ix_rank_model_run_status", "status"),
        Index("ix_rank_model_run_created_at", "created_at"),
    )


class RankActivationEvent(Base):
    """Immutable audit log of rank activation events."""

    __tablename__ = "rank_activation_event"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    previous_state = Column(JSONB, nullable=True)
    new_state = Column(JSONB, nullable=False)
    reason = Column(Text, nullable=True)
    confirmation_phrase = Column(String(200), nullable=True)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rank_model_run.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    run = relationship("RankModelRun")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        Index("ix_rank_activation_event_created_at", "created_at"),
        Index("ix_rank_activation_event_run_id", "run_id"),
    )


class RankConfig(Base):
    """Rank configuration (policy settings)."""

    __tablename__ = "rank_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_version = Column(String(50), nullable=False, server_default="rank_v1")
    config_json = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("policy_version", name="uq_rank_config_policy_version"),)
