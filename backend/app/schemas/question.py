"""Schemas for Questions."""

from datetime import datetime

from pydantic import BaseModel, Field


class QuestionBase(BaseModel):
    """Base schema for question."""

    theme_id: int = Field(..., gt=0, description="Theme ID")
    question_text: str = Field(..., min_length=1, description="Question text")
    options: list[str] = Field(
        ..., min_items=5, max_items=5, description="List of 5 answer options"
    )
    correct_option_index: int = Field(..., ge=0, le=4, description="Index of correct option (0-4)")
    explanation: str | None = Field(None, description="Explanation for the answer")
    tags: list[str] | None = Field(None, description="Tags for categorization")
    difficulty: str | None = Field(None, description="Difficulty level: easy, medium, hard")
    is_published: bool = Field(default=False, description="Whether the question is published")


class QuestionCreate(QuestionBase):
    """Schema for creating a question."""

    pass


class QuestionUpdate(BaseModel):
    """Schema for updating a question."""

    theme_id: int | None = Field(None, gt=0)
    question_text: str | None = Field(None, min_length=1)
    options: list[str] | None = Field(None, min_items=5, max_items=5)
    correct_option_index: int | None = Field(None, ge=0, le=4)
    explanation: str | None = None
    tags: list[str] | None = None
    difficulty: str | None = None
    is_published: bool | None = None


class QuestionResponse(QuestionBase):
    """Question response schema."""

    id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
