"""Mock blueprint and generation models."""

import uuid
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class MockBlueprintMode(str, Enum):
    """Mock blueprint mode."""

    EXAM = "EXAM"
    TUTOR = "TUTOR"


class MockBlueprintStatus(str, Enum):
    """Mock blueprint status."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class MockGenerationRunStatus(str, Enum):
    """Mock generation run status."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class MockBlueprint(Base):
    """Mock blueprint definition."""

    __tablename__ = "mock_blueprint"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    year = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    mode = Column(
        ENUM(MockBlueprintMode, name="mock_blueprint_mode", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=MockBlueprintMode.EXAM.value,
    )
    status = Column(
        ENUM(MockBlueprintStatus, name="mock_blueprint_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=MockBlueprintStatus.DRAFT.value,
    )
    config = Column(JSONB, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    versions = relationship("MockBlueprintVersion", back_populates="blueprint", cascade="all, delete-orphan")
    generation_runs = relationship("MockGenerationRun", back_populates="blueprint", cascade="all, delete-orphan")
    instances = relationship("MockInstance", back_populates="blueprint", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_mock_blueprint_year_status", "year", "status"),
        Index("ix_mock_blueprint_updated_at", "updated_at"),
    )


class MockBlueprintVersion(Base):
    """Version history for mock blueprint config changes."""

    __tablename__ = "mock_blueprint_version"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blueprint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mock_blueprint.id", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(Integer, nullable=False)
    config = Column(JSONB, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    diff_summary = Column(Text, nullable=True)

    # Relationships
    blueprint = relationship("MockBlueprint", back_populates="versions")
    generation_runs = relationship("MockGenerationRun", back_populates="config_version")

    __table_args__ = (
        UniqueConstraint("blueprint_id", "version", name="uq_mock_blueprint_version_blueprint_version"),
        Index("ix_mock_blueprint_version_blueprint_id", "blueprint_id"),
    )


class MockGenerationRun(Base):
    """Mock generation run tracking."""

    __tablename__ = "mock_generation_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blueprint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mock_blueprint.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        ENUM(MockGenerationRunStatus, name="mock_generation_run_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=MockGenerationRunStatus.QUEUED.value,
    )
    seed = Column(Integer, nullable=False)
    config_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mock_blueprint_version.id", onupdate="CASCADE"),
        nullable=True,
    )
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    generated_question_count = Column(Integer, nullable=False, server_default="0")
    warnings = Column(JSONB, nullable=True)
    errors = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    blueprint = relationship("MockBlueprint", back_populates="generation_runs")
    config_version = relationship("MockBlueprintVersion", back_populates="generation_runs")
    instances = relationship("MockInstance", back_populates="generation_run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_mock_generation_run_blueprint_created", "blueprint_id", "created_at"),
        Index("ix_mock_generation_run_status", "status"),
    )


class MockInstance(Base):
    """Generated mock instance (question set)."""

    __tablename__ = "mock_instance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blueprint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mock_blueprint.id", ondelete="CASCADE"),
        nullable=False,
    )
    generation_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mock_generation_run.id", ondelete="CASCADE"),
        nullable=False,
    )
    year = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    seed = Column(Integer, nullable=False)
    question_ids = Column(JSONB, nullable=False)  # Array of question_id strings (ordered)
    meta = Column(JSONB, nullable=True)  # Coverage stats, difficulty distribution, etc.
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    blueprint = relationship("MockBlueprint", back_populates="instances")
    generation_run = relationship("MockGenerationRun", back_populates="instances")

    __table_args__ = (
        Index("ix_mock_instance_blueprint_id", "blueprint_id"),
        Index("ix_mock_instance_generation_run_id", "generation_run_id"),
        Index("ix_mock_instance_created_at", "created_at"),
    )
