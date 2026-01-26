"""Models for search indexing (outbox + sync runs)."""

import uuid
from enum import Enum as PyEnum
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class SearchOutboxEventType(str, PyEnum):
    """Event types for search outbox."""

    QUESTION_PUBLISHED = "QUESTION_PUBLISHED"
    QUESTION_UNPUBLISHED = "QUESTION_UNPUBLISHED"
    QUESTION_UPDATED = "QUESTION_UPDATED"
    QUESTION_DELETED = "QUESTION_DELETED"


class SearchOutboxStatus(str, PyEnum):
    """Status for search outbox events."""

    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class SearchSyncRunType(str, PyEnum):
    """Type of sync run."""

    INCREMENTAL = "incremental"
    NIGHTLY = "nightly"


class SearchSyncRunStatus(str, PyEnum):
    """Status for sync runs."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED_FROZEN = "blocked_frozen"
    DISABLED = "disabled"


class SearchOutbox(Base):
    """Outbox table for search indexing events (outbox pattern)."""

    __tablename__ = "search_outbox"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(
        ENUM(SearchOutboxEventType, name="search_outbox_event_type", create_type=False),
        nullable=False,
    )
    payload = Column(JSONB, nullable=False)  # {question_id, version_id}
    status = Column(
        ENUM(SearchOutboxStatus, name="search_outbox_status", create_type=False),
        nullable=False,
        default=SearchOutboxStatus.PENDING,
    )
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_search_outbox_status_next_attempt", "status", "next_attempt_at"),
        Index("ix_search_outbox_event_type", "event_type"),
    )


class SearchSyncRun(Base):
    """Run registry for search sync jobs (incremental + nightly)."""

    __tablename__ = "search_sync_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_type = Column(
        ENUM(SearchSyncRunType, name="search_sync_run_type", create_type=False),
        nullable=False,
    )
    status = Column(
        ENUM(SearchSyncRunStatus, name="search_sync_run_status", create_type=False),
        nullable=False,
        default=SearchSyncRunStatus.QUEUED,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    indexed_count = Column(Integer, nullable=False, default=0)
    deleted_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    details = Column(JSONB, nullable=True)  # Additional metrics, errors, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_search_sync_run_status", "status"),
        Index("ix_search_sync_run_run_type", "run_type"),
        Index("ix_search_sync_run_created_at", "created_at"),
    )
