"""Weak labeling from v0 rules for Mistake Engine v1 training."""

import logging
from typing import Any

from app.learning_engine.mistakes.v0 import (
    MISTAKE_TYPE_CHANGED_ANSWER_WRONG,
    MISTAKE_TYPE_DISTRACTED_WRONG,
    MISTAKE_TYPE_FAST_WRONG,
    MISTAKE_TYPE_KNOWLEDGE_GAP,
    MISTAKE_TYPE_SLOW_WRONG,
    MISTAKE_TYPE_TIME_PRESSURE_WRONG,
    classify_mistake_v0,
)
from app.learning_engine.mistakes_v1.schemas import AttemptFeaturesV1, WeakLabel

logger = logging.getLogger(__name__)


def generate_weak_label(
    features: AttemptFeaturesV1,
    params: dict[str, Any],
) -> WeakLabel | None:
    """
    Generate weak label from v0 rules with confidence.

    Confidence rules:
    - Deterministic patterns (e.g., "changed answer from correct->wrong") → high confidence (0.9-1.0)
    - Ambiguous patterns → lower confidence (0.6-0.8)
    - Fallback (KNOWLEDGE_GAP) → medium confidence (0.7)

    Only wrong answers are labeled. Correct answers return None.

    Args:
        features: Attempt features
        params: v0 algorithm parameters

    Returns:
        WeakLabel or None if answer is correct
    """
    # Only label wrong answers
    if features.is_correct:
        return None

    # Use v0 classifier to get mistake type
    # Convert v1 features to v0 AttemptFeatures format
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
        return None

    mistake_type = classification.mistake_type
    rule_fired = classification.evidence.get("rule_fired", mistake_type)

    # Compute confidence based on rule type and evidence strength
    confidence = compute_label_confidence(features, mistake_type, rule_fired, params)

    return WeakLabel(
        mistake_type=mistake_type,
        confidence=confidence,
        rule_fired=rule_fired,
    )


def compute_label_confidence(
    features: AttemptFeaturesV1,
    mistake_type: str,
    rule_fired: str,
    params: dict[str, Any],
) -> float:
    """
    Compute confidence for weak label based on rule type and evidence.

    Args:
        features: Attempt features
        mistake_type: Predicted mistake type
        rule_fired: Which rule fired
        params: Algorithm parameters

    Returns:
        Confidence score in [0, 1]
    """
    # High confidence: Deterministic patterns
    if mistake_type == MISTAKE_TYPE_CHANGED_ANSWER_WRONG:
        # Changed answer is very clear signal
        if features.changed_answer_count >= 2:
            return 0.95  # Multiple changes = very confident
        return 0.90  # Single change = high confidence

    if mistake_type == MISTAKE_TYPE_TIME_PRESSURE_WRONG:
        # Time pressure is clear if remaining time is very low
        if features.time_remaining_at_answer is not None:
            time_pressure_threshold = params.get("time_pressure_remaining_sec", 60)
            if features.time_remaining_at_answer <= time_pressure_threshold * 0.5:
                return 0.90  # Very low remaining time = high confidence
            if features.time_remaining_at_answer <= time_pressure_threshold:
                return 0.80  # Within threshold = good confidence
        return 0.70  # Missing time data = lower confidence

    # Medium-high confidence: Clear behavioral signals
    if mistake_type == MISTAKE_TYPE_DISTRACTED_WRONG:
        blur_threshold = params.get("blur_threshold", 1)
        if features.pause_blur_count >= blur_threshold * 2:
            return 0.85  # Multiple blur events = high confidence
        if features.pause_blur_count >= blur_threshold:
            return 0.75  # Single blur = medium-high confidence
        return 0.65  # Edge case = lower confidence

    # Medium confidence: Time-based rules (can be ambiguous)
    if mistake_type == MISTAKE_TYPE_FAST_WRONG:
        fast_threshold = params.get("fast_wrong_sec", 20)
        if features.response_time_seconds is not None:
            if features.response_time_seconds <= fast_threshold * 0.5:
                return 0.85  # Very fast = high confidence
            if features.response_time_seconds <= fast_threshold:
                return 0.75  # Within threshold = medium-high confidence
        return 0.65  # Missing time data = lower confidence

    if mistake_type == MISTAKE_TYPE_SLOW_WRONG:
        slow_threshold = params.get("slow_wrong_sec", 90)
        if features.response_time_seconds is not None:
            if features.response_time_seconds >= slow_threshold * 1.5:
                return 0.80  # Very slow = high confidence
            if features.response_time_seconds >= slow_threshold:
                return 0.70  # Within threshold = medium confidence
        return 0.60  # Missing time data = lower confidence

    # Medium confidence: Fallback
    if mistake_type == MISTAKE_TYPE_KNOWLEDGE_GAP:
        # Knowledge gap is fallback, so medium confidence
        # But if we have strong evidence it's NOT other types, confidence increases
        has_clear_negative_evidence = (
            features.changed_answer_count == 0
            and (features.time_remaining_at_answer is None or features.time_remaining_at_answer > params.get("time_pressure_remaining_sec", 60))
            and features.pause_blur_count == 0
            and features.response_time_seconds is not None
            and params.get("fast_wrong_sec", 20) < features.response_time_seconds < params.get("slow_wrong_sec", 90)
        )
        if has_clear_negative_evidence:
            return 0.75  # Clear that it's not other types = higher confidence
        return 0.70  # Default fallback confidence

    # Default: medium confidence
    return 0.70


def generate_weak_labels_batch(
    features_list: list[AttemptFeaturesV1],
    params: dict[str, Any],
) -> list[tuple[AttemptFeaturesV1, WeakLabel]]:
    """
    Generate weak labels for a batch of attempts.

    Args:
        features_list: List of attempt features
        params: v0 algorithm parameters

    Returns:
        List of (features, weak_label) tuples for wrong answers only
    """
    results = []

    for features in features_list:
        weak_label = generate_weak_label(features, params)
        if weak_label:
            results.append((features, weak_label))

    return results
