"""Pydantic schemas for bookmarks."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Bookmark Schemas
# ============================================================================


class BookmarkCreate(BaseModel):
    """Request to create a bookmark."""

    question_id: UUID = Field(..., description="Question ID to bookmark")
    notes: str | None = Field(None, description="Optional user notes")


class BookmarkUpdate(BaseModel):
    """Request to update a bookmark's notes."""

    notes: str | None = Field(None, description="Updated notes")


class BookmarkOut(BaseModel):
    """Bookmark response."""

    id: UUID
    user_id: UUID
    question_id: UUID
    notes: str | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class BookmarkWithQuestion(BaseModel):
    """Bookmark with question details."""

    id: UUID
    user_id: UUID
    question_id: UUID
    notes: str | None
    created_at: datetime
    updated_at: datetime | None

    # Question details
    question_stem: str
    question_status: str
    year_id: int | None
    block_id: int | None
    theme_id: int | None
    difficulty: str | None
    cognitive_level: str | None
