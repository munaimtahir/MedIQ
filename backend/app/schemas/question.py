"""Schemas for Questions."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# Validation caps (input hardening)
STEM_MAX_LENGTH = 4000
EXPLANATION_MAX_LENGTH = 12000
OPTION_MAX_LENGTH = 500
TAGS_MAX_ITEMS = 50


class QuestionBase(BaseModel):
    """Base schema for question."""

    theme_id: int = Field(..., gt=0, description="Theme ID")
    question_text: str = Field(
        ..., min_length=1, max_length=STEM_MAX_LENGTH, description="Question text (stem)"
    )
    options: list[str] = Field(
        ...,
        min_length=5,
        max_length=5,
        description="List of exactly 5 answer options",
    )
    correct_option_index: int = Field(..., ge=0, le=4, description="Index of correct option (0-4)")
    explanation: str | None = Field(
        None, max_length=EXPLANATION_MAX_LENGTH, description="Explanation for the answer"
    )
    tags: list[str] | None = Field(
        None, max_length=TAGS_MAX_ITEMS, description="Tags for categorization"
    )
    difficulty: str | None = Field(None, description="Difficulty level: easy, medium, hard")
    is_published: bool = Field(default=False, description="Whether the question is published")

    @field_validator("options", mode="before")
    @classmethod
    def options_length_caps(cls, v: list[str]) -> list[str]:
        if not isinstance(v, list):
            return v
        for i, opt in enumerate(v):
            if isinstance(opt, str) and len(opt) > OPTION_MAX_LENGTH:
                raise ValueError(
                    f"options[{i}] must be at most {OPTION_MAX_LENGTH} characters"
                )
        return v


class QuestionCreate(QuestionBase):
    """Schema for creating a question."""

    pass


class QuestionUpdate(BaseModel):
    """Schema for updating a question."""

    theme_id: int | None = Field(None, gt=0)
    question_text: str | None = Field(None, min_length=1, max_length=STEM_MAX_LENGTH)
    options: list[str] | None = Field(None, min_length=5, max_length=5)
    correct_option_index: int | None = Field(None, ge=0, le=4)
    explanation: str | None = Field(None, max_length=EXPLANATION_MAX_LENGTH)
    tags: list[str] | None = Field(None, max_length=TAGS_MAX_ITEMS)
    difficulty: str | None = None
    is_published: bool | None = None

    @field_validator("options", mode="before")
    @classmethod
    def options_length_caps(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not isinstance(v, list):
            return v
        for i, opt in enumerate(v):
            if isinstance(opt, str) and len(opt) > OPTION_MAX_LENGTH:
                raise ValueError(
                    f"options[{i}] must be at most {OPTION_MAX_LENGTH} characters"
                )
        return v


class QuestionResponse(QuestionBase):
    """Question response schema."""

    id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class QuestionLegacyListItem(BaseModel):
    """Slim question list item (legacy admin list)."""

    question_id: int
    stem_snippet: str
    status: str
    theme_id: int
    difficulty: str | None = None
    cognitive: str | None = None
    updated_at: datetime | None = None
