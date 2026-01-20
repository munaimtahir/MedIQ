"""Typed contracts for learning engine inputs/outputs."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Algorithm Version & Parameters
# ============================================================================


class AlgoVersionOut(BaseModel):
    """Algorithm version output schema."""

    id: UUID
    algo_key: str
    version: str
    status: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class AlgoParamsOut(BaseModel):
    """Algorithm parameters output schema."""

    id: UUID
    algo_version_id: UUID
    params_json: dict[str, Any]
    checksum: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by_user_id: UUID | None


class AlgoRunOut(BaseModel):
    """Algorithm run output schema."""

    id: UUID
    algo_version_id: UUID
    params_id: UUID
    user_id: UUID | None
    session_id: UUID | None
    trigger: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    input_summary_json: dict[str, Any]
    output_summary_json: dict[str, Any]
    error_message: str | None


# ============================================================================
# API Response Models
# ============================================================================


class AlgorithmInfo(BaseModel):
    """Information about a single algorithm."""

    algo_key: str
    active_version: str
    status: str
    active_params: dict[str, Any]
    updated_at: datetime


class LearningEngineInfo(BaseModel):
    """Learning engine information response."""

    algorithms: list[AlgorithmInfo]


# ============================================================================
# Algorithm Input/Output Contracts (Stubs for Future)
# ============================================================================


class MasteryInput(BaseModel):
    """Input for mastery algorithm."""

    user_id: UUID
    block_id: int | None = None
    theme_id: int | None = None


class MasteryOutput(BaseModel):
    """Output from mastery algorithm."""

    user_id: UUID
    mastery_scores: dict[str, float]
    computed_at: datetime


class RevisionInput(BaseModel):
    """Input for revision scheduling algorithm."""

    user_id: UUID
    current_date: datetime


class RevisionOutput(BaseModel):
    """Output from revision scheduling algorithm."""

    user_id: UUID
    due_questions: list[UUID]
    computed_at: datetime


class DifficultyInput(BaseModel):
    """Input for difficulty assessment algorithm."""

    question_id: UUID


class DifficultyOutput(BaseModel):
    """Output from difficulty assessment algorithm."""

    question_id: UUID
    difficulty_score: float
    confidence: float
    computed_at: datetime


class AdaptiveInput(BaseModel):
    """Input for adaptive question selection algorithm."""

    user_id: UUID
    session_mode: str
    count: int
    constraints: dict[str, Any] = Field(default_factory=dict)


class AdaptiveOutput(BaseModel):
    """Output from adaptive question selection algorithm."""

    user_id: UUID
    selected_questions: list[UUID]
    reasoning: dict[str, Any]
    computed_at: datetime


class MistakesInput(BaseModel):
    """Input for common mistakes identification algorithm."""

    theme_id: int
    min_frequency: int = 3


class MistakesOutput(BaseModel):
    """Output from common mistakes identification algorithm."""

    theme_id: int
    common_patterns: list[dict[str, Any]]
    computed_at: datetime
