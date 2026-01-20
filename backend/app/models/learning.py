"""Learning engine database models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AlgoVersion(Base):
    """Algorithm version tracking."""

    __tablename__ = "algo_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    algo_key = Column(String(50), nullable=False)  # mastery, revision, etc.
    version = Column(String(50), nullable=False)  # v0, v1, etc.
    status = Column(String(20), nullable=False)  # ACTIVE, DEPRECATED, EXPERIMENTAL
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    params = relationship("AlgoParams", back_populates="algo_version", cascade="all, delete-orphan")
    runs = relationship("AlgoRun", back_populates="algo_version")

    __table_args__ = (
        UniqueConstraint("algo_key", "version", name="uq_algo_key_version"),
        Index("ix_algo_versions_algo_key_status", "algo_key", "status"),
    )


class AlgoParams(Base):
    """Algorithm parameter sets."""

    __tablename__ = "algo_params"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    algo_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("algo_versions.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    params_json = Column(JSONB, nullable=False, default={})
    checksum = Column(String(64), nullable=True)  # SHA256 hex digest
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE"),
        nullable=True,
    )

    # Relationships
    algo_version = relationship("AlgoVersion", back_populates="params")
    created_by = relationship("User")
    runs = relationship("AlgoRun", back_populates="params")

    __table_args__ = (
        Index("ix_algo_params_algo_version_id_is_active", "algo_version_id", "is_active"),
    )


class AlgoRun(Base):
    """Algorithm execution run logs."""

    __tablename__ = "algo_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE"),
        nullable=True,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("test_sessions.id", onupdate="CASCADE"),
        nullable=True,
    )

    trigger = Column(String(20), nullable=False)  # manual, submit, nightly, cron, api
    status = Column(String(20), nullable=False)  # RUNNING, SUCCESS, FAILED

    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    input_summary_json = Column(JSONB, nullable=False, default={})
    output_summary_json = Column(JSONB, nullable=False, default={})
    error_message = Column(Text, nullable=True)

    # Relationships
    algo_version = relationship("AlgoVersion", back_populates="runs")
    params = relationship("AlgoParams", back_populates="runs")
    user = relationship("User")
    session = relationship("TestSession")

    __table_args__ = (
        Index("ix_algo_runs_user_id_started_at", "user_id", "started_at"),
        Index("ix_algo_runs_algo_version_id_started_at", "algo_version_id", "started_at"),
        Index("ix_algo_runs_session_id", "session_id"),
    )
