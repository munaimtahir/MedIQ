"""Mistake classification database models."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class MistakeLog(Base):
    """Log of classified mistakes from student attempts."""

    __tablename__ = "mistake_log"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and session reference
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("test_sessions.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    position = Column(Integer, nullable=True)  # Order in session

    # Frozen tags (for stability and performance)
    year = Column(Integer, nullable=True)
    block_id = Column(
        UUID(as_uuid=True),
        ForeignKey("blocks.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    theme_id = Column(
        UUID(as_uuid=True),
        ForeignKey("themes.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )

    # Outcome
    is_correct = Column(Boolean, nullable=False)  # Will be false for v0
    mistake_type = Column(String, nullable=False)  # FAST_WRONG, SLOW_WRONG, etc.
    severity = Column(SmallInteger, nullable=True)  # 1-3

    # Explainability
    evidence_json = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Algo provenance
    algo_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("algo_versions.id", onupdate="CASCADE"),
        nullable=False,
    )
    params_id = Column(
        UUID(as_uuid=True),
        ForeignKey("algo_params.id", onupdate="CASCADE"),
        nullable=False,
    )
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("algo_runs.id", onupdate="CASCADE"),
        nullable=False,
    )

    # Relationships
    user = relationship("User")
    session = relationship("TestSession")
    question = relationship("Question")
    block = relationship("Block")
    theme = relationship("Theme")
    algo_version = relationship("AlgoVersion")
    params = relationship("AlgoParams")
    run = relationship("AlgoRun")

    __table_args__ = (
        # One classification per question attempt
        UniqueConstraint("session_id", "question_id", name="uq_mistake_log_session_question"),
        # Indexes
        Index("ix_mistake_log_user_id", "user_id"),
        Index("ix_mistake_log_session_id", "session_id"),
        Index("ix_mistake_log_question_id", "question_id"),
        Index("ix_mistake_log_user_created", "user_id", "created_at"),
        Index("ix_mistake_log_mistake_type", "mistake_type"),
        Index("ix_mistake_log_year", "year"),
        Index("ix_mistake_log_block_id", "block_id"),
        Index("ix_mistake_log_theme_id", "theme_id"),
        Index("ix_mistake_log_algo_version_id", "algo_version_id"),
        Index("ix_mistake_log_params_id", "params_id"),
        Index("ix_mistake_log_run_id", "run_id"),
        Index("ix_mistake_log_model_version_id", "model_version_id"),
        Index("ix_mistake_log_source", "source"),
    )

    # v1 fields (nullable for backward compatibility)
    source = Column(String(20), nullable=True)  # RULE_V0, MODEL_V1
    model_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mistake_model_version.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    confidence = Column(Numeric(5, 4), nullable=True)  # Prediction confidence [0, 1]

    # Relationship
    model_version = relationship("MistakeModelVersion", foreign_keys=[model_version_id])


class MistakeModelVersion(Base):
    """Model version registry for Mistake Engine v1."""

    __tablename__ = "mistake_model_version"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Status
    status = Column(String(20), nullable=False)  # DRAFT, ACTIVE, ROLLED_BACK

    # Model metadata
    model_type = Column(String(20), nullable=False)  # LOGREG, LGBM
    feature_schema_version = Column(String(50), nullable=False)
    label_schema_version = Column(String(50), nullable=False)

    # Training window
    training_window_start = Column(Date(), nullable=True)
    training_window_end = Column(Date(), nullable=True)

    # Metrics
    metrics_json = Column(JSONB, nullable=False, default={})

    # Artifact storage
    artifact_path = Column(Text(), nullable=True)  # Path to model file

    # Calibration
    calibration_type = Column(String(20), nullable=True)  # NONE, SIGMOID, ISOTONIC

    # Notes
    notes = Column(Text(), nullable=True)

    # Relationships
    training_runs = relationship("MistakeTrainingRun", back_populates="model_version", cascade="all, delete-orphan")
    inference_logs = relationship("MistakeInferenceLog", back_populates="model_version")
    mistake_logs = relationship("MistakeLog", back_populates="model_version")

    __table_args__ = (
        Index("ix_mistake_model_version_status", "status"),
        Index("ix_mistake_model_version_created_at", "created_at"),
    )


class MistakeTrainingRun(Base):
    """Training run logs for Mistake Engine v1."""

    __tablename__ = "mistake_training_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mistake_model_version.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Dataset info
    data_row_count = Column(Integer(), nullable=True)
    class_distribution_json = Column(JSONB, nullable=True)

    # Training config
    hyperparams_json = Column(JSONB, nullable=True)
    git_commit = Column(String(100), nullable=True)

    # Run metadata
    run_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )

    # Outcome
    success = Column(Boolean(), nullable=False, server_default="false")
    error_text = Column(Text(), nullable=True)

    # Relationships
    model_version = relationship("MistakeModelVersion", back_populates="training_runs")
    run_by_user = relationship("User", foreign_keys=[run_by])

    __table_args__ = (
        Index("ix_mistake_training_run_model_version_id", "model_version_id"),
        Index("ix_mistake_training_run_started_at", "started_at"),
    )


class MistakeInferenceLog(Base):
    """Append-only inference log for Mistake Engine v1 (sampled)."""

    __tablename__ = "mistake_inference_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Entity references
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_id = Column(UUID(as_uuid=True), nullable=True)  # Composite identifier
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("test_sessions.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )

    # Model reference
    model_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mistake_model_version.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )

    # Prediction results
    fallback_used = Column(Boolean(), nullable=False, server_default="false")
    predicted_type = Column(String(50), nullable=True)
    confidence = Column(Numeric(5, 4), nullable=True)

    # Explainability
    top_features_json = Column(JSONB, nullable=True)
    raw_features_json = Column(JSONB, nullable=True)  # Optional, can be gated/sampled

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    question = relationship("Question", foreign_keys=[question_id])
    session = relationship("TestSession", foreign_keys=[session_id])
    model_version = relationship("MistakeModelVersion", back_populates="inference_logs")

    __table_args__ = (
        Index("ix_mistake_inference_log_user_id", "user_id"),
        Index("ix_mistake_inference_log_occurred_at", "occurred_at"),
        Index("ix_mistake_inference_log_model_version_id", "model_version_id"),
        Index("ix_mistake_inference_log_fallback_used", "fallback_used"),
    )
