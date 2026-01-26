"""Job execution and locking models."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class JobRun(Base):
    """Job execution tracking."""

    __tablename__ = "job_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_key = Column(String(100), nullable=False)  # e.g. "revision_queue_regen"
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, server_default="QUEUED")  # QUEUED, RUNNING, SUCCEEDED, FAILED
    stats_json = Column(JSONB, nullable=False, server_default="{}")  # processed_users, due_items, errors
    error_text = Column(Text(), nullable=True)

    __table_args__ = (
        Index("ix_job_run_job_key", "job_key"),
        Index("ix_job_run_status", "status"),
        Index("ix_job_run_scheduled_for", "scheduled_for"),
    )


class JobLock(Base):
    """Job locking mechanism to prevent concurrent execution."""

    __tablename__ = "job_lock"

    job_key = Column(String(100), primary_key=True)
    locked_until = Column(DateTime(timezone=True), nullable=False)
    locked_by = Column(String(100), nullable=True)  # Process/host identifier
