"""Neo4j sync run tracking models."""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, Text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class Neo4jSyncRunType(str, PyEnum):
    """Type of Neo4j sync run."""

    INCREMENTAL = "incremental"
    FULL = "full"


class Neo4jSyncRunStatus(str, PyEnum):
    """Status for Neo4j sync runs."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED_FROZEN = "blocked_frozen"
    DISABLED = "disabled"


class Neo4jSyncRun(Base):
    """Neo4j sync run tracking for concept graph."""

    __tablename__ = "neo4j_sync_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_type = Column(
        ENUM(Neo4jSyncRunType, name="neo4j_sync_run_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status = Column(
        ENUM(Neo4jSyncRunStatus, name="neo4j_sync_run_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=Neo4jSyncRunStatus.QUEUED.value,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    nodes_upserted = Column(Integer, nullable=False, server_default="0")
    edges_upserted = Column(Integer, nullable=False, server_default="0")
    nodes_inactivated = Column(Integer, nullable=False, server_default="0")
    edges_inactivated = Column(Integer, nullable=False, server_default="0")
    cycle_detected = Column(Boolean, nullable=False, server_default="false")
    last_error = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)  # Additional metrics, cycle paths, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_neo4j_sync_run_status", "status"),
        Index("ix_neo4j_sync_run_run_type", "run_type"),
        Index("ix_neo4j_sync_run_created_at", "created_at"),
    )
