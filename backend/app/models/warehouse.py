"""Warehouse export models for Snowflake data pipeline."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class WarehouseExportRunType(str, Enum):
    """Warehouse export run type."""

    INCREMENTAL = "incremental"
    BACKFILL = "backfill"
    FULL_REBUILD = "full_rebuild"


class WarehouseExportRunStatus(str, Enum):
    """Warehouse export run status."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED_DISABLED = "blocked_disabled"
    BLOCKED_FROZEN = "blocked_frozen"
    SHADOW_DONE_FILES_ONLY = "shadow_done_files_only"


class WarehouseExportDataset(str, Enum):
    """Warehouse export dataset type."""

    ATTEMPTS = "attempts"
    EVENTS = "events"
    MASTERY = "mastery"
    REVISION_QUEUE = "revision_queue"
    DIM_QUESTION = "dim_question"
    DIM_SYLLABUS = "dim_syllabus"
    ALL = "all"


class WarehouseExportRun(Base):
    """Warehouse export run tracking."""

    __tablename__ = "warehouse_export_run"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_type = Column(
        ENUM(WarehouseExportRunType, name="warehouse_export_run_type", create_type=False),
        nullable=False,
    )
    status = Column(
        ENUM(WarehouseExportRunStatus, name="warehouse_export_run_status", create_type=False),
        nullable=False,
        server_default=WarehouseExportRunStatus.QUEUED.value,
    )
    dataset = Column(
        ENUM(WarehouseExportDataset, name="warehouse_export_dataset", create_type=False),
        nullable=False,
    )
    range_start = Column(DateTime(timezone=True), nullable=True)
    range_end = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    rows_exported = Column(Integer, nullable=False, server_default="0")
    files_written = Column(Integer, nullable=False, server_default="0")
    manifest_path = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_warehouse_export_run_dataset_created", "dataset", "created_at"),
        Index("ix_warehouse_export_run_status", "status"),
    )


class WarehouseExportState(Base):
    """Singleton state table for warehouse export watermarks."""

    __tablename__ = "warehouse_export_state"

    id = Column(Integer, primary_key=True, server_default="1")
    attempts_watermark = Column(DateTime(timezone=True), nullable=True)
    events_watermark = Column(DateTime(timezone=True), nullable=True)
    mastery_watermark = Column(DateTime(timezone=True), nullable=True)
    revision_queue_watermark = Column(Date, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_warehouse_export_state_id", "id"),
    )
