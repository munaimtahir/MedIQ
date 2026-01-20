"""Mistake classification database models."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Boolean, UniqueConstraint
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
    )
