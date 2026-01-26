"""Pydantic schemas for import system."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.import_schema import ImportFileType, ImportJobStatus

# Validation caps (input hardening)
SCHEMA_NAME_MAX_LENGTH = 200
DELIMITER_MAX_LENGTH = 16
QUOTE_CHAR_MAX_LENGTH = 16
ENCODING_MAX_LENGTH = 64
MAPPING_JSON_MAX_KEYS = 80
RULES_JSON_MAX_KEYS = 80

# ============================================================================
# Import Schema Schemas
# ============================================================================


class ImportSchemaBase(BaseModel):
    """Base schema for import configuration."""

    name: str = Field(..., max_length=SCHEMA_NAME_MAX_LENGTH, description="Schema name")
    file_type: ImportFileType = Field(default=ImportFileType.CSV, description="File type")
    delimiter: str = Field(
        default=",", max_length=DELIMITER_MAX_LENGTH, description="CSV delimiter"
    )
    quote_char: str = Field(
        default='"', max_length=QUOTE_CHAR_MAX_LENGTH, description="CSV quote character"
    )
    has_header: bool = Field(default=True, description="Whether CSV has header row")
    encoding: str = Field(
        default="utf-8", max_length=ENCODING_MAX_LENGTH, description="File encoding"
    )
    mapping_json: dict[str, Any] = Field(..., description="Field mapping configuration")
    rules_json: dict[str, Any] = Field(..., description="Validation rules and defaults")

    @model_validator(mode="after")
    def cap_json_keys(self) -> "ImportSchemaBase":
        if len(self.mapping_json) > MAPPING_JSON_MAX_KEYS:
            raise ValueError(
                f"mapping_json must have at most {MAPPING_JSON_MAX_KEYS} keys"
            )
        if len(self.rules_json) > RULES_JSON_MAX_KEYS:
            raise ValueError(f"rules_json must have at most {RULES_JSON_MAX_KEYS} keys")
        return self


class ImportSchemaCreate(ImportSchemaBase):
    """Schema for creating import schema."""

    pass


class ImportSchemaUpdate(BaseModel):
    """Schema for updating import schema (creates new version)."""

    name: str | None = Field(None, max_length=SCHEMA_NAME_MAX_LENGTH)
    file_type: ImportFileType | None = None
    delimiter: str | None = Field(None, max_length=DELIMITER_MAX_LENGTH)
    quote_char: str | None = Field(None, max_length=QUOTE_CHAR_MAX_LENGTH)
    has_header: bool | None = None
    encoding: str | None = Field(None, max_length=ENCODING_MAX_LENGTH)
    mapping_json: dict[str, Any] | None = None
    rules_json: dict[str, Any] | None = None

    @field_validator("mapping_json")
    @classmethod
    def mapping_json_key_cap(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None and len(v) > MAPPING_JSON_MAX_KEYS:
            raise ValueError(
                f"mapping_json must have at most {MAPPING_JSON_MAX_KEYS} keys"
            )
        return v

    @field_validator("rules_json")
    @classmethod
    def rules_json_key_cap(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None and len(v) > RULES_JSON_MAX_KEYS:
            raise ValueError(
                f"rules_json must have at most {RULES_JSON_MAX_KEYS} keys"
            )
        return v


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
