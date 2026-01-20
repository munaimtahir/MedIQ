"""Pydantic schemas for BKT API."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BKTParamsResponse(BaseModel):
    """BKT parameters response."""
    
    p_L0: float = Field(..., description="Prior probability of mastery")
    p_T: float = Field(..., description="Probability of learning (transition)")
    p_S: float = Field(..., description="Probability of slip")
    p_G: float = Field(..., description="Probability of guess")
    concept_id: Optional[str] = None
    algo_version_id: Optional[str] = None
    is_default: bool = Field(False, description="Whether these are default fallback params")


class MasteryStateResponse(BaseModel):
    """User mastery state response."""
    
    concept_id: str
    p_mastery: float = Field(..., ge=0.0, le=1.0, description="Current mastery probability")
    n_attempts: int = Field(..., ge=0)
    last_attempt_at: Optional[str] = None
    is_mastered: bool = Field(..., description="Whether mastery threshold is met")
    updated_at: str


class UpdateFromAttemptRequest(BaseModel):
    """Request to update mastery from an attempt."""
    
    user_id: Optional[UUID] = Field(None, description="User ID (admin only, otherwise current user)")
    question_id: UUID
    concept_id: UUID
    correct: bool
    create_snapshot: bool = Field(False, description="Whether to create historical snapshot")
    meta: Optional[dict] = Field(None, description="Optional metadata")


class UpdateFromAttemptResponse(BaseModel):
    """Response from mastery update."""
    
    user_id: str
    concept_id: str
    question_id: str
    correct: bool
    p_mastery_prior: float
    p_mastery_new: float
    mastery_change: float
    n_attempts: int
    params_used: dict
    bkt_metadata: dict
    snapshot_created: bool


class GetMasteryRequest(BaseModel):
    """Request to get user mastery states."""
    
    user_id: Optional[UUID] = Field(None, description="User ID (admin only)")
    concept_ids: Optional[list[UUID]] = Field(None, description="Optional concept filter")


class GetMasteryResponse(BaseModel):
    """Response with mastery states."""
    
    user_id: str
    states: list[MasteryStateResponse]
    total: int


class RecomputeMasteryRequest(BaseModel):
    """Request to recompute/retrain BKT parameters."""
    
    concept_ids: Optional[list[UUID]] = Field(None, description="Concepts to retrain (None = all)")
    from_date: Optional[datetime] = Field(None, description="Start of training data window")
    to_date: Optional[datetime] = Field(None, description="End of training data window")
    min_attempts: int = Field(10, ge=1, description="Minimum attempts required to fit")
    activate: bool = Field(False, description="Whether to activate fitted params")
    dry_run: bool = Field(False, description="If true, fit but don't persist")


class RecomputeMasteryResponse(BaseModel):
    """Response from recompute/retrain job."""
    
    run_id: str
    algo_version: str
    concepts_processed: int
    concepts_fitted: int
    concepts_skipped: int
    metrics_summary: dict
    dry_run: bool
    activated: bool
