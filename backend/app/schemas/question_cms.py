"""Pydantic schemas for CMS Question Bank."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.question_cms import ChangeKind, MediaRole, QuestionStatus

# Validation caps (input hardening)
STEM_MAX_LENGTH = 4000
EXPLANATION_MAX_LENGTH = 12000
OPTION_MAX_LENGTH = 500


class QuestionBase(BaseModel):
    """Base schema for question (shared fields)."""

    stem: str | None = Field(
        None, max_length=STEM_MAX_LENGTH, description="Question stem (supports markdown/latex)"
    )
    option_a: str | None = Field(None, max_length=OPTION_MAX_LENGTH, description="Option A")
    option_b: str | None = Field(None, max_length=OPTION_MAX_LENGTH, description="Option B")
    option_c: str | None = Field(None, max_length=OPTION_MAX_LENGTH, description="Option C")
    option_d: str | None = Field(None, max_length=OPTION_MAX_LENGTH, description="Option D")
    option_e: str | None = Field(None, max_length=OPTION_MAX_LENGTH, description="Option E")
    correct_index: int | None = Field(None, ge=0, le=4, description="Correct option index (0-4)")
    explanation_md: str | None = Field(
        None, max_length=EXPLANATION_MAX_LENGTH, description="Explanation in markdown"
    )
    year_id: int | None = Field(None, description="Year ID")
    block_id: int | None = Field(None, description="Block ID")
    theme_id: int | None = Field(None, description="Theme ID")
    topic_id: int | None = Field(None, description="Topic ID (optional)")
    concept_id: int | None = Field(None, description="Concept ID (optional)")
    cognitive_level: str | None = Field(None, description="Cognitive level")
    difficulty: str | None = Field(None, description="Difficulty level")
    source_book: str | None = Field(None, description="Source book")
    source_page: str | None = Field(None, description="Source page (e.g., 'p. 12-13')")
    source_ref: str | None = Field(None, description="Source reference")


class QuestionCreate(QuestionBase):
    """Schema for creating a question. Exactly 5 options required."""

    @model_validator(mode="after")
    def exactly_five_options(self) -> "QuestionCreate":
        opts = [self.option_a, self.option_b, self.option_c, self.option_d, self.option_e]
        if any(opt is None or not str(opt).strip() for opt in opts):
            raise ValueError("All 5 options (option_a through option_e) must be non-empty")
        return self


class QuestionUpdate(BaseModel):
    """Schema for updating a question (all fields optional)."""

    stem: str | None = Field(None, max_length=STEM_MAX_LENGTH)
    option_a: str | None = Field(None, max_length=OPTION_MAX_LENGTH)
    option_b: str | None = Field(None, max_length=OPTION_MAX_LENGTH)
    option_c: str | None = Field(None, max_length=OPTION_MAX_LENGTH)
    option_d: str | None = Field(None, max_length=OPTION_MAX_LENGTH)
    option_e: str | None = Field(None, max_length=OPTION_MAX_LENGTH)
    correct_index: int | None = Field(None, ge=0, le=4)
    explanation_md: str | None = Field(None, max_length=EXPLANATION_MAX_LENGTH)
    year_id: int | None = None
    block_id: int | None = None
    theme_id: int | None = None
    topic_id: int | None = None
    concept_id: int | None = None
    cognitive_level: str | None = None
    difficulty: str | None = None
    source_book: str | None = None
    source_page: str | None = None
    source_ref: str | None = None


class QuestionOut(QuestionBase):
    """Question response schema."""

    id: UUID
    status: QuestionStatus
    created_by: UUID
    updated_by: UUID
    approved_by: UUID | None
    approved_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class QuestionListOut(BaseModel):
    """Question list item (simplified for listing)."""

    id: UUID
    stem: str | None
    status: QuestionStatus
    year_id: int | None
    block_id: int | None
    theme_id: int | None
    difficulty: str | None
    cognitive_level: str | None
    source_book: str | None = None
    source_page: str | None = None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class WorkflowActionOut(BaseModel):
    """Response for workflow actions."""

    message: str
    question_id: UUID
    previous_status: QuestionStatus
    new_status: QuestionStatus


class RejectRequest(BaseModel):
    """Request body for reject action."""

    reason: str = Field(..., min_length=1, description="Reason for rejection")


class VersionOut(BaseModel):
    """Question version response."""

    id: UUID
    question_id: UUID
    version_no: int
    snapshot: dict[str, Any]
    change_kind: ChangeKind
    change_reason: str | None
    changed_by: UUID
    changed_at: datetime

    class Config:
        from_attributes = True


class MediaOut(BaseModel):
    """Media asset response."""

    id: UUID
    storage_provider: str
    path: str
    mime_type: str
    size_bytes: int
    sha256: str | None
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class MediaAttachIn(BaseModel):
    """Request to attach media to question."""

    media_id: UUID = Field(..., description="Media asset ID")
    role: MediaRole = Field(..., description="Role of media in question")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: MediaRole) -> MediaRole:
        """Validate media role."""
        return v


class QuestionListQuery(BaseModel):
    """Query parameters for question listing."""

    status: QuestionStatus | None = None
    year_id: int | None = None
    block_id: int | None = None
    theme_id: int | None = None
    difficulty: str | None = None
    cognitive_level: str | None = None
    source_book: str | None = None
    q: str | None = Field(None, max_length=500, description="Text search on stem")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Page size")
