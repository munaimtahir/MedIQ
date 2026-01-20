"""Pydantic schemas for import system."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.import_schema import ImportFileType, ImportJobStatus


# ============================================================================
# Import Schema Schemas
# ============================================================================


class ImportSchemaBase(BaseModel):
    """Base schema for import configuration."""

    name: str = Field(..., description="Schema name")
    file_type: ImportFileType = Field(default=ImportFileType.CSV, description="File type")
    delimiter: str = Field(default=",", description="CSV delimiter")
    quote_char: str = Field(default='"', description="CSV quote character")
    has_header: bool = Field(default=True, description="Whether CSV has header row")
    encoding: str = Field(default="utf-8", description="File encoding")
    mapping_json: dict[str, Any] = Field(..., description="Field mapping configuration")
    rules_json: dict[str, Any] = Field(..., description="Validation rules and defaults")


class ImportSchemaCreate(ImportSchemaBase):
    """Schema for creating import schema."""

    pass


class ImportSchemaUpdate(BaseModel):
    """Schema for updating import schema (creates new version)."""

    name: str | None = None
    file_type: ImportFileType | None = None
    delimiter: str | None = None
    quote_char: str | None = None
    has_header: bool | None = None
    encoding: str | None = None
    mapping_json: dict[str, Any] | None = None
    rules_json: dict[str, Any] | None = None


class ImportSchemaOut(ImportSchemaBase):
    """Import schema response."""

    id: UUID
    version: int
    is_active: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class ImportSchemaListOut(BaseModel):
    """Import schema list item."""

    id: UUID
    name: str
    version: int
    is_active: bool
    file_type: ImportFileType
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


# ============================================================================
# Import Job Schemas
# ============================================================================


class ImportJobCreate(BaseModel):
    """Schema for creating import job (internal)."""

    schema_id: UUID
    schema_name: str
    schema_version: int
    created_by: UUID
    filename: str
    file_type: ImportFileType
    dry_run: bool = False


class ImportJobOut(BaseModel):
    """Import job response."""

    id: UUID
    schema_id: UUID | None
    schema_name: str
    schema_version: int
    created_by: UUID
    filename: str
    file_type: ImportFileType
    dry_run: bool
    status: ImportJobStatus
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    summary_json: dict[str, Any] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class ImportJobListOut(BaseModel):
    """Import job list item."""

    id: UUID
    schema_name: str
    schema_version: int
    filename: str
    dry_run: bool
    status: ImportJobStatus
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class ImportJobRowOut(BaseModel):
    """Import job rejected row."""

    id: UUID
    job_id: UUID
    row_number: int
    external_id: str | None
    raw_row_json: dict[str, Any]
    errors_json: list[dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Request/Response Schemas
# ============================================================================


class ActivateSchemaResponse(BaseModel):
    """Response for schema activation."""

    message: str
    schema_id: UUID
    is_active: bool


class ImportJobResultOut(BaseModel):
    """Immediate response after import job creation."""

    job_id: UUID
    status: ImportJobStatus
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    summary_json: dict[str, Any] | None
