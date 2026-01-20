"""Pydantic schemas for Learning Engine API."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Shared Response Envelope
# ============================================================================


class AlgoInfo(BaseModel):
    """Algorithm identification."""

    key: str
    version: str


class LearningResponse(BaseModel):
    """Standard response envelope for all learning endpoints."""

    ok: bool = True
    run_id: UUID
    algo: AlgoInfo
    params_id: UUID
    summary: dict[str, Any]


# ============================================================================
# Task 111: Mastery Recompute
# ============================================================================


class MasteryRecomputeRequest(BaseModel):
    """Request to recompute mastery scores."""

    user_id: UUID | None = None
    year: int = Field(..., ge=1, le=6)
    block_id: UUID | None = None
    theme_id: UUID | None = None
    dry_run: bool = False


class MasteryRecomputeSummary(BaseModel):
    """Summary of mastery recompute."""

    themes_processed: int
    records_upserted: int
    dry_run: bool


# ============================================================================
# Task 112: Revision Plan
# ============================================================================


class RevisionPlanRequest(BaseModel):
    """Request to generate revision queue."""

    user_id: UUID | None = None
    year: int = Field(..., ge=1, le=6)
    block_id: UUID | None = None


class RevisionPlanSummary(BaseModel):
    """Summary of revision plan generation."""

    generated: int
    due_today: int


# ============================================================================
# Task 113: Adaptive Next
# ============================================================================


class AdaptiveNextRequest(BaseModel):
    """Request for adaptive question selection."""

    user_id: UUID | None = None
    year: int = Field(..., ge=1, le=6)
    block_ids: list[UUID] = Field(..., min_length=1)
    theme_ids: list[UUID] | None = None
    count: int = Field(..., ge=1, le=100)
    mode: str = Field(..., pattern="^(tutor|exam)$")
    source: str = Field(default="weakness", pattern="^(revision|weakness)$")

    @field_validator("block_ids")
    @classmethod
    def validate_block_ids(cls, v):
        if not v:
            raise ValueError("At least one block_id required")
        return v


class AdaptiveNextSummary(BaseModel):
    """Summary of adaptive question selection."""

    count: int
    themes_used: list[UUID]
    difficulty_distribution: dict[str, int]
    question_ids: list[UUID]


# ============================================================================
# Task 114: Difficulty Update
# ============================================================================


class DifficultyUpdateRequest(BaseModel):
    """Request to update question difficulty."""

    session_id: UUID


class DifficultyUpdateSummary(BaseModel):
    """Summary of difficulty update."""

    questions_updated: int
    avg_delta: float


# ============================================================================
# Task 115: Mistakes Classify
# ============================================================================


class MistakesClassifyRequest(BaseModel):
    """Request to classify mistakes."""

    session_id: UUID


class MistakesClassifySummary(BaseModel):
    """Summary of mistake classification."""

    total_wrong: int
    classified: int
    counts_by_type: dict[str, int]
