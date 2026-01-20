"""Question difficulty calibration database models."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class QuestionDifficulty(Base):
    """Live difficulty rating per question using ELO-lite."""

    __tablename__ = "question_difficulty"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Question reference
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Difficulty metrics
    rating = Column(Numeric(8, 2), nullable=False, default=1000)
    attempts = Column(Integer, nullable=False, default=0)
    correct = Column(Integer, nullable=False, default=0)
    p_correct = Column(Numeric(5, 4), nullable=True)  # Cached correct/attempts

    # Audit
    last_updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

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

    # Explainability
    breakdown_json = Column(JSONB, nullable=False, default={})

    # Relationships
    question = relationship("Question")
    algo_version = relationship("AlgoVersion")
    params = relationship("AlgoParams")
    run = relationship("AlgoRun")

    __table_args__ = (
        Index("ix_question_difficulty_question_id", "question_id"),
        Index("ix_question_difficulty_rating", "rating"),
        Index("ix_question_difficulty_attempts", "attempts"),
        Index("ix_question_difficulty_algo_version_id", "algo_version_id"),
        Index("ix_question_difficulty_params_id", "params_id"),
        Index("ix_question_difficulty_run_id", "run_id"),
    )
