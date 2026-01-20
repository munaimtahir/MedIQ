"""
Pydantic schemas for difficulty calibration API.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AttemptUpdate(BaseModel):
    """Single attempt for difficulty update."""

    attempt_id: Optional[UUID] = None
    question_id: UUID
    theme_id: Optional[UUID] = None
    score: bool
    occurred_at: Optional[datetime] = None


class UpdateDifficultyRequest(BaseModel):
    """Request to update difficulty from attempts."""

    session_id: Optional[UUID] = None
    attempts: list[AttemptUpdate]


class UpdateDifficultyResponse(BaseModel):
    """Response from difficulty update."""

    ok: bool
    algo_version: str
    updates_count: int
    avg_p_pred: float
    errors: list[str] = Field(default_factory=list)


class RatingInfo(BaseModel):
    """Rating information for a scope."""

    rating: float
    uncertainty: float
    n_attempts: int
    last_seen_at: Optional[datetime]


class QuestionDifficultyResponse(BaseModel):
    """Response for question difficulty lookup."""

    question_id: UUID
    global_rating: RatingInfo
    theme_ratings: dict[str, RatingInfo] = Field(default_factory=dict)


class UserAbilityResponse(BaseModel):
    """Response for user ability lookup."""

    user_id: UUID
    global_rating: RatingInfo
    theme_ratings: dict[str, RatingInfo] = Field(default_factory=dict)


class HealthMetrics(BaseModel):
    """System health metrics."""

    total_users: int
    total_questions: int
    total_updates: int
    recent_updates_24h: int
    logloss_30d: float
    brier_30d: float
    ece_30d: float
    mean_question_rating: float
    drift_detected: bool


class RecenterResponse(BaseModel):
    """Response from recenter operation."""

    ok: bool
    mean_adjustment: float
    questions_updated: int
    users_updated: int
    already_centered: bool


class CalibrationBin(BaseModel):
    """Single bin in calibration curve."""

    bin_start: float
    bin_end: float
    predicted_mean: float
    observed_freq: float
    count: int


class MetricsResponse(BaseModel):
    """Detailed metrics response."""

    logloss: float
    brier: float
    ece: float
    calibration_curve: list[CalibrationBin]
    window_days: int
