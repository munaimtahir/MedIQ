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
    block_ids: list[int] = Field(..., min_length=1, max_length=200)
    theme_ids: list[int] | None = Field(None, max_length=200)
    count: int = Field(..., ge=1, le=100)
    mode: str = Field(..., pattern="^(tutor|exam|revision)$")
    source: str = Field(default="mixed", pattern="^(mixed|revision|weakness)$")

    @field_validator("block_ids")
    @classmethod
    def validate_block_ids(cls, v):
        if not v:
            raise ValueError("At least one block_id required")
        return v


class AdaptiveNextSummary(BaseModel):
    """Summary of adaptive question selection (v0 format)."""

    count: int
    themes_used: list[int]
    difficulty_distribution: dict[str, int]
    question_ids: list[UUID]


# =============================================================================
# Adaptive v1 Schemas (Thompson Sampling with constraints)
# =============================================================================


class ThemePlanItem(BaseModel):
    """Single theme in the selection plan."""

    theme_id: int
    quota: int
    base_priority: float
    sampled_y: float
    final_score: float


class PlanStats(BaseModel):
    """Statistics from question selection."""

    excluded_recent: int = 0
    explore_used: int = 0
    avg_p_correct: float = 0.0


class ChallengeBand(BaseModel):
    """Elo challenge band parameters."""

    low: float
    high: float


class AdaptivePlanV1(BaseModel):
    """Full selection plan for v1 response."""

    themes: list[ThemePlanItem]
    due_ratio: float
    p_band: ChallengeBand
    stats: PlanStats


class AdaptiveNextResponseV1(BaseModel):
    """Response for adaptive question selection v1."""

    ok: bool = True
    run_id: UUID
    algo: AlgoInfo
    params_id: UUID | None
    question_ids: list[UUID]
    plan: AdaptivePlanV1


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
