"""Pydantic schemas for test sessions."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.session import SessionMode, SessionStatus


# ============================================================================
# Session Schemas
# ============================================================================


class SessionCreate(BaseModel):
    """Request to create a test session."""

    mode: SessionMode = Field(..., description="Session mode (TUTOR or EXAM)")
    year: int = Field(..., ge=1, le=2, description="Year (1 or 2)")
    blocks: list[str] = Field(..., description="Block codes (e.g., ['A', 'B'])")
    themes: list[int] | None = Field(
        None, description="Theme IDs (optional, null = all themes in blocks)"
    )
    count: int = Field(..., ge=1, le=200, description="Number of questions")
    duration_seconds: int | None = Field(
        None, ge=60, description="Test duration in seconds (optional for TUTOR)"
    )
    difficulty: list[str] | None = Field(None, description="Filter by difficulty levels")
    cognitive: list[str] | None = Field(None, description="Filter by cognitive levels")


class SessionProgress(BaseModel):
    """Session progress summary."""

    answered_count: int
    marked_for_review_count: int
    current_position: int  # 1-based


class SessionQuestionSummary(BaseModel):
    """Question summary in session (no content, just status)."""

    position: int
    question_id: UUID
    has_answer: bool
    marked_for_review: bool


class SessionOut(BaseModel):
    """Session response."""

    id: UUID
    user_id: UUID
    mode: SessionMode
    status: SessionStatus
    year: int
    blocks_json: list[str]
    themes_json: list[int] | None
    total_questions: int
    started_at: datetime
    submitted_at: datetime | None
    duration_seconds: int | None
    expires_at: datetime | None
    score_correct: int | None
    score_total: int | None
    score_pct: float | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class SessionStateOut(BaseModel):
    """Session state with progress and questions."""

    session: SessionOut
    progress: SessionProgress
    questions: list[SessionQuestionSummary]


class SessionCreateResponse(BaseModel):
    """Response after creating session."""

    session_id: UUID
    status: SessionStatus
    mode: SessionMode
    total_questions: int
    started_at: datetime
    expires_at: datetime | None
    progress: SessionProgress


# ============================================================================
# Answer Schemas
# ============================================================================


class AnswerSubmit(BaseModel):
    """Submit answer for a question."""

    question_id: UUID = Field(..., description="Question ID")
    selected_index: int | None = Field(
        None, ge=0, le=4, description="Selected option index (0-4), null to clear"
    )
    marked_for_review: bool | None = Field(None, description="Mark for review flag")


class AnswerOut(BaseModel):
    """Answer response."""

    id: UUID
    session_id: UUID
    question_id: UUID
    selected_index: int | None
    is_correct: bool | None
    answered_at: datetime | None
    changed_count: int
    marked_for_review: bool
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class AnswerSubmitResponse(BaseModel):
    """Response after submitting answer."""

    answer: AnswerOut
    progress: SessionProgress


# ============================================================================
# Submit & Review Schemas
# ============================================================================


class SessionSubmitResponse(BaseModel):
    """Response after submitting session."""

    session_id: UUID
    status: SessionStatus
    score_correct: int
    score_total: int
    score_pct: float
    submitted_at: datetime


class ReviewQuestionContent(BaseModel):
    """Frozen question content for review."""

    question_id: UUID
    position: int
    stem: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    option_e: str
    correct_index: int
    explanation_md: str | None
    # Optional metadata
    year_id: int | None = None
    block_id: int | None = None
    theme_id: int | None = None
    source_book: str | None = None
    source_page: str | None = None


class ReviewAnswer(BaseModel):
    """User's answer in review."""

    question_id: UUID
    selected_index: int | None
    is_correct: bool | None
    marked_for_review: bool
    answered_at: datetime | None
    changed_count: int


class ReviewItem(BaseModel):
    """Single item in review (question + answer)."""

    question: ReviewQuestionContent
    answer: ReviewAnswer


class SessionReviewOut(BaseModel):
    """Complete review response."""

    session: SessionOut
    items: list[ReviewItem]  # Ordered by position


# ============================================================================
# Current Question (for GET state)
# ============================================================================


class CurrentQuestionOut(BaseModel):
    """Current question content (without answer/explanation)."""

    question_id: UUID
    position: int
    stem: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    option_e: str
    # Metadata
    year_id: int | None = None
    block_id: int | None = None
    theme_id: int | None = None


class SessionStateWithCurrentOut(BaseModel):
    """Session state including current question content."""

    session: SessionOut
    progress: SessionProgress
    questions: list[SessionQuestionSummary]
    current_question: CurrentQuestionOut | None
