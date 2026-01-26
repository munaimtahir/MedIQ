"""Runtime inference for Mistake Engine v1 with cold-start safety."""

import logging
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.constants import AlgoKey
from app.learning_engine.mistakes.service import classify_mistakes_v0_for_session
from app.learning_engine.mistakes.v0 import classify_mistake_v0
from app.learning_engine.mistakes.features import AttemptFeatures
from app.learning_engine.mistakes_v1.features import extract_features_v1_for_attempt, features_to_dict
from app.learning_engine.mistakes_v1.registry import get_active_model_version, load_model_artifact
from app.learning_engine.mistakes_v1.schemas import (
    MistakePrediction,
    MistakeSource,
    ModelStatus,
)
from app.learning_engine.registry import resolve_active
from app.models.mistakes import MistakeInferenceLog, MistakeLog

logger = logging.getLogger(__name__)

# Confidence threshold for fallback (configurable, initially conservative)
CONF_THRESHOLD = 0.5  # TODO: Make this configurable and derived from validation data


async def classify_attempt_v1(
    db: AsyncSession,
    session_id: UUID,
    question_id: UUID,
    user_id: UUID | None = None,
    log_inference: bool = True,
    inference_log_sample_rate: float = 0.1,  # Log 10% of inferences
) -> MistakePrediction | None:
    """
    Classify an attempt using v1 model with fallback to v0.

    Cold-start logic:
    - If no ACTIVE model: use v0 rule engine (RULE_V0)
    - Else compute features and predict
    - If max_prob < CONF_THRESHOLD => fallback to v0 rule engine
    - Save result to mistake_log with source=MODEL_V1 or RULE_V0

    Args:
        db: Database session
        session_id: Session ID
        question_id: Question ID
        user_id: User ID (if not provided, will be fetched)
        log_inference: Whether to log inference (for sampling)
        inference_log_sample_rate: Rate at which to log inferences

    Returns:
        MistakePrediction or None if answer is correct
    """
    # Extract features
    features = await extract_features_v1_for_attempt(db, session_id, question_id, user_id)
    if not features:
        logger.warning(f"Failed to extract features for session {session_id}, question {question_id}")
        return None

    # Only classify wrong answers
    if features.is_correct:
        return None

    # Check for active model
    active_model_version = await get_active_model_version(db)
    if not active_model_version or active_model_version.status != ModelStatus.ACTIVE:
        logger.info("No active model, using v0 fallback")
        return await _classify_with_v0_fallback(db, features, session_id, question_id, user_id)

    # Load model
    model, metadata = load_model_artifact(active_model_version.id)
    if model is None:
        logger.warning(f"Failed to load model artifact for version {active_model_version.id}, using v0 fallback")
        return await _classify_with_v0_fallback(db, features, session_id, question_id, user_id)

    # Prepare features for model
    feature_dict = features_to_dict(features)
    feature_array = _dict_to_feature_array(feature_dict, metadata)

    # Predict
    try:
        # Handle LightGBM models (they have predict_proba but need different input)
        if hasattr(model, "predict") and not hasattr(model, "predict_proba"):
            # LightGBM Booster
            probabilities = model.predict(feature_array.reshape(1, -1), num_iteration=model.best_iteration if hasattr(model, "best_iteration") else None)
            # LightGBM returns probabilities for each class
            if len(probabilities.shape) == 1:
                probabilities = probabilities.reshape(1, -1)
            probabilities = probabilities[0]
        else:
            # Sklearn-compatible model
            probabilities = model.predict_proba([feature_array])[0]
        
        predicted_class_idx = np.argmax(probabilities)
        max_confidence = float(probabilities[predicted_class_idx])

        # Get class names from model
        class_names = metadata.get("class_names", []) if metadata else []
        if not class_names and hasattr(model, "classes_"):
            class_names = list(model.classes_)

        if predicted_class_idx < len(class_names):
            predicted_type = class_names[predicted_class_idx]
        else:
            logger.warning(f"Invalid class index {predicted_class_idx}, using v0 fallback")
            return await _classify_with_v0_fallback(db, features, session_id, question_id, user_id)

        # Check confidence threshold
        if max_confidence < CONF_THRESHOLD:
            logger.info(f"Low confidence ({max_confidence:.3f} < {CONF_THRESHOLD}), using v0 fallback")
            return await _classify_with_v0_fallback(db, features, session_id, question_id, user_id)

        # Get top features (feature importance)
        top_features = _get_top_features(feature_dict, model, metadata, top_k=5)

        prediction = MistakePrediction(
            mistake_type=predicted_type,
            confidence=max_confidence,
            top_features=top_features,
            model_version_id=active_model_version.id,
            fallback_used=False,
            source=MistakeSource.MODEL_V1,
        )

        # Save to mistake_log
        await _save_mistake_log(db, features, prediction, session_id, question_id, user_id)

        # Log inference (sampled)
        if log_inference and np.random.random() < inference_log_sample_rate:
            await _log_inference(db, features, prediction, session_id, question_id, user_id, active_model_version.id)

        return prediction

    except Exception as e:
        logger.error(f"Error during model inference: {e}", exc_info=True)
        return await _classify_with_v0_fallback(db, features, session_id, question_id, user_id)


async def _classify_with_v0_fallback(
    db: AsyncSession,
    features: Any,  # AttemptFeaturesV1
    session_id: UUID,
    question_id: UUID,
    user_id: UUID | None,
) -> MistakePrediction:
    """
    Classify using v0 rule engine as fallback.

    Args:
        db: Database session
        features: Attempt features
        session_id: Session ID
        question_id: Question ID
        user_id: User ID

    Returns:
        MistakePrediction with source=RULE_V0
    """
    # Resolve v0 params
    version, params_obj = await resolve_active(db, AlgoKey.MISTAKES.value)
    if not version or not params_obj:
        logger.warning("No active v0 algorithm found, using default params")
        params = {}
    else:
        params = params_obj.params_json

    # Convert to v0 AttemptFeatures
    from app.learning_engine.mistakes.features import AttemptFeatures

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

    classification = classify_mistake_v0(v0_features, params)
    if not classification:
        # Should not happen since we already checked is_correct=False
        logger.error("v0 classification returned None for wrong answer")
        return None

    prediction = MistakePrediction(
        mistake_type=classification.mistake_type,
        confidence=0.8,  # Default confidence for v0 rules
        top_features={},
        model_version_id=None,
        fallback_used=True,
        source=MistakeSource.RULE_V0,
    )

    # Save to mistake_log
    await _save_mistake_log(db, features, prediction, session_id, question_id, user_id)

    return prediction


async def _save_mistake_log(
    db: AsyncSession,
    features: Any,  # AttemptFeaturesV1
    prediction: MistakePrediction,
    session_id: UUID,
    question_id: UUID,
    user_id: UUID | None,
) -> None:
    """
    Save classification result to mistake_log.

    Args:
        db: Database session
        features: Attempt features
        prediction: Prediction result
        session_id: Session ID
        question_id: Question ID
        user_id: User ID
    """
    # Get or create mistake_log entry
    from sqlalchemy.dialects.postgresql import insert

    from app.models.mistakes import MistakeLog
    from app.models.session import TestSession

    # Get session for user_id if not provided
    if user_id is None:
        session = await db.get(TestSession, session_id)
        if session:
            user_id = session.user_id

    if not user_id:
        logger.warning("Cannot save mistake_log: user_id not available")
        return

    # Get algo version and params for v0 (needed for mistake_log structure)
    version, params_obj = await resolve_active(db, AlgoKey.MISTAKES.value)
    if not version or not params_obj:
        logger.warning("Cannot save mistake_log: no active algo version")
        return

    # Create mistake_log entry
    record = {
        "user_id": user_id,
        "session_id": session_id,
        "question_id": question_id,
        "position": features.position,
        "year": features.year,
        "block_id": features.block_id,
        "theme_id": features.theme_id,
        "is_correct": features.is_correct,
        "mistake_type": prediction.mistake_type,
        "severity": 2,  # Default severity
        "evidence_json": {"source": prediction.source.value, "confidence": prediction.confidence},
        "source": prediction.source.value,
        "model_version_id": prediction.model_version_id,
        "confidence": prediction.confidence,
        "algo_version_id": version.id,
        "params_id": params_obj.id,
        # run_id will be set by service layer if needed
    }

    # Use upsert to handle conflicts
    stmt = insert(MistakeLog).values(record)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_mistake_log_session_question",
        set_={
            "mistake_type": stmt.excluded.mistake_type,
            "source": stmt.excluded.source,
            "model_version_id": stmt.excluded.model_version_id,
            "confidence": stmt.excluded.confidence,
            "evidence_json": stmt.excluded.evidence_json,
        },
    )
    await db.execute(stmt)
    await db.commit()


async def _log_inference(
    db: AsyncSession,
    features: Any,  # AttemptFeaturesV1
    prediction: MistakePrediction,
    session_id: UUID,
    question_id: UUID,
    user_id: UUID | None,
    model_version_id: UUID,
) -> None:
    """
    Log inference to mistake_inference_log (sampled).

    Args:
        db: Database session
        features: Attempt features
        prediction: Prediction result
        session_id: Session ID
        question_id: Question ID
        user_id: User ID
        model_version_id: Model version ID
    """
    if user_id is None:
        from app.models.session import TestSession

        session = await db.get(TestSession, session_id)
        if session:
            user_id = session.user_id

    if not user_id:
        return

    inference_log = MistakeInferenceLog(
        user_id=user_id,
        session_id=session_id,
        question_id=question_id,
        model_version_id=model_version_id,
        fallback_used=prediction.fallback_used,
        predicted_type=prediction.mistake_type,
        confidence=prediction.confidence,
        top_features_json=prediction.top_features,
        # raw_features_json can be omitted for privacy/performance
    )

    db.add(inference_log)
    await db.commit()


def _dict_to_feature_array(feature_dict: dict[str, Any], metadata: dict[str, Any] | None) -> np.ndarray:
    """
    Convert feature dictionary to numpy array for model input.

    Args:
        feature_dict: Feature dictionary
        metadata: Model metadata (may contain feature order)

    Returns:
        Feature array
    """
    # If metadata has feature_order, use it
    if metadata and "feature_order" in metadata:
        feature_order = metadata["feature_order"]
        return np.array([feature_dict.get(f, 0.0) for f in feature_order])
    else:
        # Default order (alphabetical)
        sorted_keys = sorted(feature_dict.keys())
        return np.array([feature_dict[k] for k in sorted_keys])


def _get_top_features(
    feature_dict: dict[str, Any],
    model: Any,
    metadata: dict[str, Any] | None,
    top_k: int = 5,
) -> dict[str, float]:
    """
    Get top contributing features for explainability.

    Args:
        feature_dict: Feature dictionary
        model: Trained model
        metadata: Model metadata
        top_k: Number of top features to return

    Returns:
        Dictionary of feature_name -> importance_score
    """
    # Try to get feature importance from model
    if hasattr(model, "feature_importances_"):
        # Tree-based model (LightGBM)
        feature_order = metadata.get("feature_order", sorted(feature_dict.keys())) if metadata else sorted(feature_dict.keys())
        importances = list(model.feature_importances_)
        feature_importance = dict(zip(feature_order, importances))
        # Sort by importance and return top_k
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_features[:top_k])
    elif hasattr(model, "coef_"):
        # Linear model (Logistic Regression)
        feature_order = metadata.get("feature_order", sorted(feature_dict.keys())) if metadata else sorted(feature_dict.keys())
        coef = model.coef_[0] if len(model.coef_.shape) > 1 else model.coef_
        importances = [abs(c) for c in coef]
        feature_importance = dict(zip(feature_order, importances))
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_features[:top_k])
    else:
        # Fallback: return empty dict
        return {}
