"""Evaluation harness database models."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class EvalRun(Base):
    """Evaluation run metadata and configuration."""

    __tablename__ = "eval_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, server_default="QUEUED")  # QUEUED, RUNNING, SUCCEEDED, FAILED

    # Suite identification
    suite_name = Column(String(100), nullable=False)  # e.g. "bkt_v1", "full_stack_v1"
    suite_versions = Column(JSONB, nullable=False, server_default="{}")  # {"bkt":"1.0.3", ...}

    # Dataset specification
    dataset_spec = Column(JSONB, nullable=False, server_default="{}")  # time_min, time_max, years, blocks, cohort_filters, split_strategy

    # Configuration
    config = Column(JSONB, nullable=False, server_default="{}")  # bins, mastery_threshold, horizons, seeds, toggles

    # Versioning
    git_sha = Column(String(100), nullable=True)
    random_seed = Column(Integer(), nullable=True)

    # Metadata
    notes = Column(Text(), nullable=True)
    error = Column(Text(), nullable=True)

    # Relationships
    metrics = relationship("EvalMetric", back_populates="run", cascade="all, delete-orphan")
    artifacts = relationship("EvalArtifact", back_populates="run", cascade="all, delete-orphan")
    curves = relationship("EvalCurve", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_eval_run_status", "status"),
        Index("ix_eval_run_created_at", "created_at"),
        Index("ix_eval_run_suite_name", "suite_name"),
    )


class EvalMetric(Base):
    """Computed metrics per evaluation run."""

    __tablename__ = "eval_metric"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("eval_run.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    metric_name = Column(String(100), nullable=False)  # e.g. "logloss", "brier", "ece", "time_to_mastery_p90"
    scope_type = Column(String(50), nullable=False)  # GLOBAL, YEAR, BLOCK, THEME, CONCEPT, USER
    scope_id = Column(String(100), nullable=True)  # ID for block/theme/concept/user
    value = Column(Numeric(12, 6), nullable=False)
    n = Column(Integer(), nullable=False)  # number of observations
    extra = Column(JSONB, nullable=True)  # optional (confidence intervals, etc.)

    # Relationships
    run = relationship("EvalRun", back_populates="metrics")

    __table_args__ = (
        Index("ix_eval_metric_run_id", "run_id"),
        Index("ix_eval_metric_metric_name", "metric_name"),
        Index("ix_eval_metric_scope", "scope_type", "scope_id"),
    )


class EvalArtifact(Base):
    """Generated artifacts (reports, plots, summaries)."""

    __tablename__ = "eval_artifact"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("eval_run.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_type = Column(String(50), nullable=False)  # REPORT_MD, RELIABILITY_BINS, CONFUSION, RAW_SUMMARY
    path = Column(Text(), nullable=True)  # Path to artifact file
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    run = relationship("EvalRun", back_populates="artifacts")

    __table_args__ = (
        Index("ix_eval_artifact_run_id", "run_id"),
        Index("ix_eval_artifact_type", "artifact_type"),
    )


class EvalCurve(Base):
    """Curve data (reliability curves, etc.)."""

    __tablename__ = "eval_curve"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("eval_run.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    curve_name = Column(String(100), nullable=False)  # e.g. "reliability_curve_p_correct"
    data = Column(JSONB, nullable=False)  # Curve data points
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    run = relationship("EvalRun", back_populates="curves")

    __table_args__ = (
        Index("ix_eval_curve_run_id", "run_id"),
        Index("ix_eval_curve_name", "curve_name"),
    )
