"""Revision scheduler database models."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class RevisionQueue(Base):
    """Spaced repetition revision queue for themes."""

    __tablename__ = "revision_queue"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and syllabus context
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    year = Column(Integer, nullable=False)
    block_id = Column(
        Integer,
        ForeignKey("blocks.id", onupdate="CASCADE"),
        nullable=False,
    )
    theme_id = Column(
        Integer,
        ForeignKey("themes.id", onupdate="CASCADE"),
        nullable=False,
    )

    # Scheduling
    due_date = Column(Date, nullable=False)
    priority_score = Column(Numeric(5, 2), nullable=False)
    recommended_count = Column(Integer, nullable=False)

    # State
    status = Column(String(20), nullable=False, default="DUE")  # DUE, DONE, SNOOZED, SKIPPED

    # Explainability
    reason_json = Column(JSONB, nullable=False, default={})

    # Audit / provenance
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
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
    block = relationship("Block")
    theme = relationship("Theme")
    algo_version = relationship("AlgoVersion")
    params = relationship("AlgoParams")
    run = relationship("AlgoRun")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "theme_id", "due_date", name="uq_revision_queue_user_theme_date"
        ),
        Index("ix_revision_queue_user_id", "user_id"),
        Index("ix_revision_queue_user_id_due_date_status", "user_id", "due_date", "status"),
        Index(
            "ix_revision_queue_user_id_priority_score",
            "user_id",
            "priority_score",
            postgresql_using="btree",
        ),
        Index("ix_revision_queue_algo_version_id", "algo_version_id"),
        Index("ix_revision_queue_params_id", "params_id"),
        Index("ix_revision_queue_run_id", "run_id"),
    )
