"""Pydantic schemas for Mistake Engine v1."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModelType(str, Enum):
    """Model type enum."""

    LOGREG = "LOGREG"
    LGBM = "LGBM"


class ModelStatus(str, Enum):
    """Model version status."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ROLLED_BACK = "ROLLED_BACK"


class CalibrationType(str, Enum):
    """Calibration method."""

    NONE = "NONE"
    SIGMOID = "SIGMOID"
    ISOTONIC = "ISOTONIC"


class MistakeSource(str, Enum):
    """Mistake classification source."""

    RULE_V0 = "RULE_V0"
    MODEL_V1 = "MODEL_V1"


# ============================================================================
# Feature Extraction Schemas
# ============================================================================


class AttemptFeaturesV1(BaseModel):
    """Extended features for v1 classification."""

    # Attempt-level
    question_id: UUID
    session_id: UUID
    user_id: UUID
    position: int | None = None
    is_correct: bool
    answered_at: datetime | None = None

    # Time features
    response_time_seconds: float | None = None
    response_time_zscore_user: float | None = None  # Z-score vs user median
    response_time_zscore_cohort: float | None = None  # Z-score vs cohort median
    time_remaining_at_answer: float | None = None

    # Answer behavior
    changed_answer_count: int = 0
    first_answer_correct: bool | None = None
    final_answer_correct: bool
    mark_for_review_used: bool = False
    pause_blur_count: int = 0  # Tab-away/blur events

    # Question context
    question_difficulty: float | None = None  # Elo rating or initial bucket
    cognitive_level: str | None = None
    block_id: UUID | None = None
    theme_id: UUID | None = None
    year: int | None = None

    # User context (cold-start safe)
    user_rolling_accuracy_last_n: float | None = None  # Last N attempts
    user_rolling_median_time_last_n: float | None = None
    session_pacing_indicator: float | None = None  # User vs cohort pacing

    class Config:
        """Pydantic config."""

        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat() if v else None,
            Decimal: float,
        }


# ============================================================================
# Weak Labeling Schemas
# ============================================================================


class WeakLabel(BaseModel):
    """Weak label with confidence."""

    mistake_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    rule_fired: str | None = None  # Which v0 rule generated this label


# ============================================================================
# Inference Schemas
# ============================================================================


class MistakePrediction(BaseModel):
    """Prediction result from v1 model."""

    mistake_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    top_features: dict[str, float] = Field(default_factory=dict)  # Feature importance
    model_version_id: UUID | None = None
    fallback_used: bool = False
    source: MistakeSource = MistakeSource.MODEL_V1


class InferenceDebugInfo(BaseModel):
    """Debug information for inference."""

    attempt_id: UUID
    features: AttemptFeaturesV1
    prediction: MistakePrediction | None = None
    v0_fallback: dict[str, Any] | None = None
    confidence_threshold: float
    model_version_id: UUID | None = None


# ============================================================================
# Training Schemas
# ============================================================================


class TrainingConfig(BaseModel):
    """Training configuration."""

    start_date: date
    end_date: date
    model_type: ModelType = ModelType.LGBM
    feature_schema_version: str = "v1.0"
    label_schema_version: str = "v1.0"
    train_split: float = Field(default=0.8, ge=0.5, le=0.95)
    calibration_type: CalibrationType = CalibrationType.ISOTONIC
    hyperparams: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class TrainingMetrics(BaseModel):
    """Training metrics."""

    macro_f1: float
    weighted_f1: float
    calibration_ece: float | None = None  # Expected Calibration Error
    confusion_matrix: list[list[int]] | None = None
    class_distribution: dict[str, int]
    train_samples: int
    val_samples: int


class ModelVersionCreate(BaseModel):
    """Request to create a new model version."""

    model_type: ModelType
    feature_schema_version: str
    label_schema_version: str
    training_window_start: date
    training_window_end: date
    metrics_json: dict[str, Any]
    artifact_path: str | None = None
    calibration_type: CalibrationType | None = None
    notes: str | None = None


class ModelVersionResponse(BaseModel):
    """Model version response."""

    id: UUID
    created_at: datetime
    status: ModelStatus
    model_type: ModelType
    feature_schema_version: str
    label_schema_version: str
    training_window_start: date | None
    training_window_end: date | None
    metrics_json: dict[str, Any]
    artifact_path: str | None
    calibration_type: CalibrationType | None
    notes: str | None

    class Config:
        """Pydantic config."""

        from_attributes = True


# ============================================================================
# API Request/Response Schemas
# ============================================================================


class ClassifyRequest(BaseModel):
    """Request to classify an attempt."""

    attempt_id: UUID | None = None  # Composite: session_id + question_id
    session_id: UUID | None = None
    question_id: UUID | None = None


class ClassifyResponse(BaseModel):
    """Classification response."""

    mistake_type: str
    confidence: float
    source: MistakeSource
    model_version_id: UUID | None = None
    top_features: dict[str, float] = Field(default_factory=dict)
    mistake_log_id: UUID | None = None


class ModelMetadataResponse(BaseModel):
    """Active model metadata."""

    model_version: ModelVersionResponse | None = None
    is_active: bool = False
    fallback_to_v0: bool = True
