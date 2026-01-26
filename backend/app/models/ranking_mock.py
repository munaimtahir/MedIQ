"""Mock exam result and ranking models (Task 145)."""

import uuid
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Float, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class RankingRunStatus(str, Enum):
    """Ranking run status."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class MockResult(Base):
    """Per-user raw score for a mock instance."""

    __tablename__ = "mock_result"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mock_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mock_instance.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    raw_score = Column(Integer, nullable=False)
    percent = Column(Float, nullable=False)
    time_taken_seconds = Column(Integer, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("mock_instance_id", "user_id", name="uq_mock_result_instance_user"),
        Index("ix_mock_result_mock_instance_id", "mock_instance_id"),
        Index("ix_mock_result_user_id", "user_id"),
    )


class MockRanking(Base):
    """Computed rank/percentile per cohort, engine-tracked."""

    __tablename__ = "mock_ranking"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mock_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mock_instance.id", ondelete="CASCADE"),
        nullable=False,
    )
    cohort_id = Column(Text, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    rank = Column(Integer, nullable=False)
    percentile = Column(Float, nullable=False)
    engine_used = Column(Text, nullable=False)  # python | go_shadow | go_active
    computed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    meta = Column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "mock_instance_id", "cohort_id", "user_id", "engine_used",
            name="uq_mock_ranking_instance_cohort_user_engine",
        ),
        Index("ix_mock_ranking_mock_instance_id", "mock_instance_id"),
        Index("ix_mock_ranking_cohort_id", "cohort_id"),
        Index("ix_mock_ranking_engine_used", "engine_used"),
    )


class RankingRun(Base):
    """Run metadata for mock ranking computation; parity_report for go_shadow."""

    __tablename__ = "ranking_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mock_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mock_instance.id", ondelete="CASCADE"),
        nullable=False,
    )
    cohort_id = Column(Text, nullable=False)
    status = Column(
        ENUM(RankingRunStatus, name="ranking_run_status", create_type=False),
        nullable=False,
        server_default=RankingRunStatus.QUEUED.value,
    )
    engine_requested = Column(Text, nullable=True)
    engine_effective = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    n_users = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)
    parity_report = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_ranking_run_mock_instance_id", "mock_instance_id"),
        Index("ix_ranking_run_cohort_id", "cohort_id"),
        Index("ix_ranking_run_status", "status"),
        Index("ix_ranking_run_created_at", "created_at"),
    )
