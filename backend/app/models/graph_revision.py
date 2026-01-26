"""Graph-aware revision planning subsystem database models.

Shadow-first module that re-ranks/augments FSRS revision plans using prerequisite
graph knowledge. Never affects student queues unless explicitly activated.
"""

import uuid
from datetime import date
from enum import Enum

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class PrereqSyncStatus(str, Enum):
    """Prerequisite sync run status."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class GraphRevisionRunStatus(str, Enum):
    """Graph revision run status."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    BLOCKED_FROZEN = "BLOCKED_FROZEN"
    DISABLED = "DISABLED"


class PrereqEdge(Base):
    """Prerequisite edge: authoritative source in Postgres (synced to Neo4j)."""

    __tablename__ = "prereq_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_theme_id = Column(
        Integer,
        ForeignKey("themes.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )  # Prerequisite theme
    to_theme_id = Column(
        Integer,
        ForeignKey("themes.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )  # Theme that requires from_theme_id
    weight = Column(Float, nullable=False, server_default="1.0")
    source = Column(String(50), nullable=False, server_default="manual")  # manual, imported, inferred
    confidence = Column(Float, nullable=True)  # 0..1 if inferred
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    from_theme = relationship("Theme", foreign_keys=[from_theme_id])
    to_theme = relationship("Theme", foreign_keys=[to_theme_id])
    created_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("from_theme_id", "to_theme_id", name="uq_prereq_edges_from_to"),
        Index("ix_prereq_edges_from_theme_id", "from_theme_id"),
        Index("ix_prereq_edges_to_theme_id", "to_theme_id"),
        Index("ix_prereq_edges_is_active", "is_active"),
    )


class PrereqSyncRun(Base):
    """Neo4j sync run tracking."""

    __tablename__ = "prereq_sync_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(
        ENUM(PrereqSyncStatus, name="prereq_sync_status", create_type=False),
        nullable=False,
        server_default="QUEUED",
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    details_json = Column(JSONB, nullable=True)  # node_count, edge_count, errors, etc.
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_prereq_sync_run_status", "status"),
        Index("ix_prereq_sync_run_created_at", "created_at"),
    )


class ShadowRevisionPlan(Base):
    """Shadow revision plan (computed but not applied unless activated)."""

    __tablename__ = "shadow_revision_plan"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    run_date = Column(Date, nullable=False)  # Date for which plan was computed
    mode = Column(String(20), nullable=False, server_default="baseline")  # baseline|shadow
    baseline_count = Column(Integer, nullable=False, server_default="0")
    injected_count = Column(Integer, nullable=False, server_default="0")
    plan_json = Column(JSONB, nullable=False, server_default="[]")  # Ordered list of plan items
    computed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("user_id", "run_date", name="uq_shadow_revision_plan_user_date"),
        Index("ix_shadow_revision_plan_user_id", "user_id"),
        Index("ix_shadow_revision_plan_run_date", "run_date"),
        Index("ix_shadow_revision_plan_mode", "mode"),
    )


class GraphRevisionRun(Base):
    """Graph revision run registry with metrics."""

    __tablename__ = "graph_revision_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_date = Column(Date, nullable=False)
    mode = Column(String(20), nullable=False, server_default="shadow")  # shadow|active
    cohort_key = Column(String(100), nullable=True)  # Optional cohort filter
    metrics = Column(JSONB, nullable=True)  # coverage, injection_rate, neo4j_availability, cycle_count
    status = Column(
        ENUM(GraphRevisionRunStatus, name="graph_revision_run_status", create_type=False),
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
    created_by = relationship("User")

    __table_args__ = (
        Index("ix_graph_revision_run_run_date", "run_date"),
        Index("ix_graph_revision_run_status", "status"),
        Index("ix_graph_revision_run_mode", "mode"),
        Index("ix_graph_revision_run_created_at", "created_at"),
    )


class GraphRevisionConfig(Base):
    """Graph revision planner configuration."""

    __tablename__ = "graph_revision_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_version = Column(String(50), nullable=False, server_default="graph_revision_v1")
    config_json = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("policy_version", name="uq_graph_revision_config_policy_version"),)


class GraphRevisionActivationEvent(Base):
    """Graph revision activation audit trail."""

    __tablename__ = "graph_revision_activation_event"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    previous_state = Column(JSONB, nullable=True)
    new_state = Column(JSONB, nullable=False)
    reason = Column(Text, nullable=True)
    confirmation_phrase = Column(String(200), nullable=True)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("graph_revision_run.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    run = relationship("GraphRevisionRun")
    created_by = relationship("User")

    __table_args__ = (
        Index("ix_graph_revision_activation_event_created_at", "created_at"),
        Index("ix_graph_revision_activation_event_run_id", "run_id"),
    )
