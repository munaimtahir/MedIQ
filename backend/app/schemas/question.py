"""Schemas for Questions."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class QuestionBase(BaseModel):
    """Base schema for question."""

    theme_id: int = Field(..., gt=0, description="Theme ID")
    question_text: str = Field(..., min_length=1, description="Question text")
    options: list[str] = Field(
        ..., min_items=5, max_items=5, description="List of 5 answer options"
    )
    correct_option_index: int = Field(..., ge=0, le=4, description="Index of correct option (0-4)")
    explanation: Optional[str] = Field(None, description="Explanation for the answer")
    tags: Optional[list[str]] = Field(None, description="Tags for categorization")
    difficulty: Optional[str] = Field(None, description="Difficulty level: easy, medium, hard")
    is_published: bool = Field(default=False, description="Whether the question is published")


class QuestionCreate(QuestionBase):
    """Schema for creating a question."""

    pass


class QuestionUpdate(BaseModel):
    """Schema for updating a question."""

    theme_id: Optional[int] = Field(None, gt=0)
    question_text: Optional[str] = Field(None, min_length=1)
    options: Optional[list[str]] = Field(None, min_items=5, max_items=5)
    correct_option_index: Optional[int] = Field(None, ge=0, le=4)
    explanation: Optional[str] = None
    tags: Optional[list[str]] = None
    difficulty: Optional[str] = None
    is_published: Optional[bool] = None


class QuestionResponse(QuestionBase):
    """Question response schema."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
