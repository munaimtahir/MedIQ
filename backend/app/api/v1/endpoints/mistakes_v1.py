"""Mistake Engine v1 API endpoints."""

import logging
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.learning_engine.mistakes_v1.infer import classify_attempt_v1
from app.learning_engine.mistakes_v1.registry import (
    activate_model_version,
    get_active_model_version,
    get_model_version_by_id,
)
from app.learning_engine.mistakes_v1.schemas import (
    ClassifyRequest,
    ClassifyResponse,
    InferenceDebugInfo,
    ModelMetadataResponse,
    ModelVersionResponse,
    TrainingConfig,
)
from app.learning_engine.mistakes_v1.train import train_model
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


# ============================================================================
# POST /v1/learning/mistakes/classify
# ============================================================================


@router.post("/learning/mistakes/classify", response_model=ClassifyResponse)
async def classify_attempt(
    request: ClassifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Classify an attempt using v1 model (with v0 fallback).

    Request body:
    - attempt_id: Optional composite identifier
    - session_id: Session ID (required if attempt_id not provided)
    - question_id: Question ID (required if attempt_id not provided)

    Returns:
    - mistake_type: Predicted mistake type
    - confidence: Prediction confidence [0, 1]
    - source: MODEL_V1 or RULE_V0
    - model_version_id: Model version used (if MODEL_V1)
    - top_features: Top contributing features
    - mistake_log_id: ID of created mistake_log entry
    """
    # Resolve session_id and question_id
    if request.attempt_id:
        # attempt_id is composite, need to parse or look up
        # For now, require session_id and question_id
        raise HTTPException(
            status_code=400,
            detail="attempt_id parsing not yet implemented. Please provide session_id and question_id.",
        )

    if not request.session_id or not request.question_id:
        raise HTTPException(
            status_code=400,
            detail="Either attempt_id or both session_id and question_id must be provided",
        )

    # Verify session ownership
    from app.models.session import TestSession

    session = await db.get(TestSession, request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.role != "ADMIN" and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    # Classify
    prediction = await classify_attempt_v1(
        db,
        request.session_id,
        request.question_id,
        session.user_id,
    )

    if not prediction:
        raise HTTPException(status_code=400, detail="Attempt is correct or not found")

    # Get mistake_log_id (would need to query after save)
    mistake_log_id = None

    return ClassifyResponse(
        mistake_type=prediction.mistake_type,
        confidence=prediction.confidence,
        source=prediction.source,
        model_version_id=prediction.model_version_id,
        top_features=prediction.top_features,
        mistake_log_id=mistake_log_id,
    )


# ============================================================================
# GET /v1/learning/mistakes/model
# ============================================================================


@router.get("/learning/mistakes/model", response_model=ModelMetadataResponse)
async def get_active_model(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get active model metadata.

    Returns:
    - model_version: Active model version info (if any)
    - is_active: Whether a model is active
    - fallback_to_v0: Whether v0 fallback is enabled
    """
    model_version = await get_active_model_version(db)

    if model_version:
        return ModelMetadataResponse(
            model_version=ModelVersionResponse.model_validate(model_version),
            is_active=True,
            fallback_to_v0=True,
        )
    else:
        return ModelMetadataResponse(
            model_version=None,
            is_active=False,
            fallback_to_v0=True,
        )


# ============================================================================
# POST /v1/learning/mistakes/model/train (Admin only)
# ============================================================================


@router.post("/learning/mistakes/model/train")
async def trigger_training(
    config: TrainingConfig,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Trigger model training (admin only).

    In development, can run inline. In production, should enqueue a job.

    Request body:
    - start_date: Training window start
    - end_date: Training window end
    - model_type: LOGREG or LGBM
    - feature_schema_version: Feature schema version
    - label_schema_version: Label schema version
    - train_split: Train/val split ratio
    - calibration_type: Calibration method
    - hyperparams: Model hyperparameters
    - notes: Optional notes

    Returns:
    - model_version_id: Created model version ID
    - metrics: Training metrics
    """
    require_admin(current_user)

    try:
        model_version_id, metrics = await train_model(db, config, current_user.id)

        return {
            "model_version_id": str(model_version_id),
            "metrics": metrics.model_dump(),
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


# ============================================================================
# POST /v1/learning/mistakes/model/activate (Admin only)
# ============================================================================


@router.post("/learning/mistakes/model/activate")
async def activate_model(
    model_version_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Activate a model version (admin only).

    Deactivates all other model versions.

    Returns:
    - model_version: Activated model version
    """
    require_admin(current_user)

    model_version = await activate_model_version(db, model_version_id)
    if not model_version:
        raise HTTPException(status_code=404, detail="Model version not found")

    return {
        "model_version_id": str(model_version.id),
        "status": model_version.status,
        "message": "Model version activated",
    }


# ============================================================================
# GET /v1/learning/mistakes/debug/{attempt_id} (Admin only)
# ============================================================================


@router.get("/learning/mistakes/debug/{session_id}/{question_id}", response_model=InferenceDebugInfo)
async def debug_inference(
    session_id: UUID,
    question_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get debug information for an attempt classification (admin only).

    Returns:
    - attempt_id: Attempt identifier
    - features: Extracted features
    - prediction: Model prediction (if available)
    - v0_fallback: v0 rule classification (if fallback used)
    - confidence_threshold: Confidence threshold used
    - model_version_id: Model version used
    """
    require_admin(current_user)

    from app.learning_engine.mistakes_v1.features import extract_features_v1_for_attempt
    from app.learning_engine.mistakes_v1.infer import CONF_THRESHOLD

    # Get features
    from app.models.session import TestSession

    session = await db.get(TestSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    features = await extract_features_v1_for_attempt(db, session_id, question_id, session.user_id)
    if not features:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # Get active model
    active_model = await get_active_model_version(db)

    # Try classification
    prediction = None
    v0_fallback = None

    if active_model:
        try:
            prediction_obj = await classify_attempt_v1(
                db, session_id, question_id, session.user_id, log_inference=False
            )
            if prediction_obj:
                prediction = prediction_obj
        except Exception as e:
            logger.warning(f"Classification failed: {e}")

    # Get v0 fallback if needed
    if not prediction or prediction.fallback_used:
        from app.learning_engine.constants import AlgoKey
        from app.learning_engine.mistakes.features import AttemptFeatures
        from app.learning_engine.mistakes.v0 import classify_mistake_v0
        from app.learning_engine.registry import resolve_active

        version, params_obj = await resolve_active(db, AlgoKey.MISTAKES.value)
        if version and params_obj:
            v0_features = AttemptFeatures(
                question_id=features.question_id,
                position=features.position,
                is_correct=features.is_correct,
                answered_at=features.answered_at,
                time_spent_sec=features.response_time_seconds,
                change_count=features.changed_answer_count,
                blur_count=features.pause_blur_count,
                mark_for_review_used=features.mark_for_review_used,
                remaining_sec_at_answer=features.time_remaining_at_answer,
                year=features.year,
                block_id=features.block_id,
                theme_id=features.theme_id,
            )
            v0_classification = classify_mistake_v0(v0_features, params_obj.params_json)
            if v0_classification:
                v0_fallback = {
                    "mistake_type": v0_classification.mistake_type,
                    "severity": v0_classification.severity,
                    "evidence": v0_classification.evidence,
                }

    return InferenceDebugInfo(
        attempt_id=question_id,  # Using question_id as attempt identifier
        features=features,
        prediction=prediction,
        v0_fallback=v0_fallback,
        confidence_threshold=CONF_THRESHOLD,
        model_version_id=active_model.id if active_model else None,
    )
