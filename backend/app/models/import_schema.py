"""Import Schema models for versioned CSV/JSON import configurations."""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ImportFileType(str, PyEnum):
    """Supported import file types."""

    CSV = "csv"
    JSON = "json"


class ImportJobStatus(str, PyEnum):
    """Import job status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImportSchema(Base):
    """Versioned import schema configuration."""

    __tablename__ = "import_schemas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=False)

    # File parsing config (values_callable so we persist "csv"/"json", not "CSV"/"JSON")
    file_type = Column(
        Enum(
            ImportFileType,
            name="import_file_type",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ImportFileType.CSV,
    )
    delimiter = Column(String(5), nullable=False, default=",")
    quote_char = Column(String(5), nullable=False, default='"')
    has_header = Column(Boolean, nullable=False, default=True)
    encoding = Column(String(20), nullable=False, default="utf-8")

    # Schema definition
    mapping_json = Column(JSONB, nullable=False)  # {canonical_field: {column: "name", ...}}
    rules_json = Column(JSONB, nullable=False)  # {required: [...], defaults: {...}, ...}

    # Metadata
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    import_jobs = relationship("ImportJob", back_populates="schema", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_import_schema_name_version"),
        Index("ix_import_schemas_is_active", "is_active"),
        Index("ix_import_schemas_name", "name"),
    )


class ImportJob(Base):
    """Import job tracking."""

    __tablename__ = "import_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Schema used (snapshot for reproducibility)
    schema_id = Column(
        UUID(as_uuid=True),
        ForeignKey("import_schemas.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    schema_name = Column(String(200), nullable=False)
    schema_version = Column(Integer, nullable=False)

    # Job metadata
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False
    )
    filename = Column(String(500), nullable=False)
    file_type = Column(
        Enum(
            ImportFileType,
            name="import_file_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    dry_run = Column(Boolean, nullable=False, default=False)

    # Status tracking
    status = Column(
        Enum(ImportJobStatus, name="import_job_status", create_type=True),
        nullable=False,
        default=ImportJobStatus.PENDING,
    )
    total_rows = Column(Integer, nullable=False, default=0)
    accepted_rows = Column(Integer, nullable=False, default=0)
    rejected_rows = Column(Integer, nullable=False, default=0)

    # Results
    summary_json = Column(JSONB, nullable=True)  # {error_counts: {...}, warnings: [...]}
    error_message = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    schema = relationship("ImportSchema", back_populates="import_jobs")
    rejected_rows = relationship("ImportJobRow", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_import_jobs_status", "status"),
        Index("ix_import_jobs_created_by", "created_by"),
        Index("ix_import_jobs_created_at", "created_at"),
    )


class ImportJobRow(Base):
    """Rejected rows from import jobs (only rejected rows stored)."""

    __tablename__ = "import_job_rows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    # Row identification
    row_number = Column(Integer, nullable=False)
    external_id = Column(String(200), nullable=True)

    # Data
    raw_row_json = Column(JSONB, nullable=False)  # Safe subset of row data
    errors_json = Column(JSONB, nullable=False)  # [{code, message, field}]

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    job = relationship("ImportJob", back_populates="rejected_rows")

    __table_args__ = (
        Index("ix_import_job_rows_job_id", "job_id"),
        Index("ix_import_job_rows_row_number", "row_number"),
    )
