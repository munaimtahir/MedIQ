"""Mastery tracking database models."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserThemeMastery(Base):
    """Per-theme mastery scores for users."""

    __tablename__ = "user_theme_mastery"

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

    # Aggregates (cached for performance)
    attempts_total = Column(Integer, nullable=False, default=0)
    correct_total = Column(Integer, nullable=False, default=0)
    accuracy_pct = Column(Numeric(5, 2), nullable=False, default=0)

    # Mastery score (0..1)
    mastery_score = Column(Numeric(6, 4), nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    computed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Provenance / audit trail
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

    # Breakdown for explainability
    breakdown_json = Column(JSONB, nullable=False, default={})

    # Relationships
    user = relationship("User")
    block = relationship("Block")
    theme = relationship("Theme")
    algo_version = relationship("AlgoVersion")
    params = relationship("AlgoParams")
    run = relationship("AlgoRun")

    __table_args__ = (
        UniqueConstraint("user_id", "theme_id", name="uq_user_theme_mastery"),
        Index("ix_user_theme_mastery_user_id", "user_id"),
        Index("ix_user_theme_mastery_user_id_mastery_score", "user_id", "mastery_score"),
        Index("ix_user_theme_mastery_user_id_computed_at", "user_id", "computed_at"),
        Index("ix_user_theme_mastery_theme_id_mastery_score", "theme_id", "mastery_score"),
        Index("ix_user_theme_mastery_algo_version_id", "algo_version_id"),
        Index("ix_user_theme_mastery_params_id", "params_id"),
        Index("ix_user_theme_mastery_run_id", "run_id"),
    )
