"""Mistake classification v0 - Rule-based classifier with precedence."""

import logging
from typing import Any

from app.learning_engine.mistakes.features import AttemptFeatures

logger = logging.getLogger(__name__)


# Mistake type constants
MISTAKE_TYPE_FAST_WRONG = "FAST_WRONG"
MISTAKE_TYPE_SLOW_WRONG = "SLOW_WRONG"
MISTAKE_TYPE_CHANGED_ANSWER_WRONG = "CHANGED_ANSWER_WRONG"
MISTAKE_TYPE_TIME_PRESSURE_WRONG = "TIME_PRESSURE_WRONG"
MISTAKE_TYPE_DISTRACTED_WRONG = "DISTRACTED_WRONG"
MISTAKE_TYPE_KNOWLEDGE_GAP = "KNOWLEDGE_GAP"


class MistakeClassification:
    """Result of mistake classification."""
    
    def __init__(
        self,
        mistake_type: str,
        severity: int,
        evidence: dict[str, Any],
    ):
        self.mistake_type = mistake_type
        self.severity = severity
        self.evidence = evidence


def classify_mistake_v0(
    features: AttemptFeatures,
    params: dict[str, Any],
) -> MistakeClassification | None:
    """
    Classify a wrong answer into a mistake type using rule-based precedence.
    
    Rule precedence (applied in order, first match wins):
    1. CHANGED_ANSWER_WRONG - if change_count >= 1
    2. TIME_PRESSURE_WRONG - if remaining_sec <= time_pressure_remaining_sec
    3. FAST_WRONG - if time_spent_sec <= fast_wrong_sec
    4. DISTRACTED_WRONG - if blur_count >= blur_threshold
    5. SLOW_WRONG - if time_spent_sec >= slow_wrong_sec
    6. KNOWLEDGE_GAP - fallback for all other wrong answers
    
    Only wrong answers are classified in v0. Correct answers return None.
    
    Args:
        features: Extracted features for the attempt
        params: Algorithm parameters
    
    Returns:
        MistakeClassification or None if answer is correct
    """
    # Only classify wrong answers
    if features.is_correct:
        return None
    
    # Extract params
    fast_wrong_sec = params.get("fast_wrong_sec", 20)
    slow_wrong_sec = params.get("slow_wrong_sec", 90)
    time_pressure_remaining_sec = params.get("time_pressure_remaining_sec", 60)
    blur_threshold = params.get("blur_threshold", 1)
    severity_rules = params.get("severity_rules", {})
    
    # Build evidence dictionary
    evidence = {
        "time_spent_sec": features.time_spent_sec,
        "change_count": features.change_count,
        "blur_count": features.blur_count,
        "remaining_sec_at_answer": features.remaining_sec_at_answer,
        "mark_for_review_used": features.mark_for_review_used,
        "thresholds": {
            "fast_wrong_sec": fast_wrong_sec,
            "slow_wrong_sec": slow_wrong_sec,
            "time_pressure_remaining_sec": time_pressure_remaining_sec,
            "blur_threshold": blur_threshold,
        },
    }
    
    mistake_type = None
    
    # Apply rules in precedence order
    
    # Rule 1: Changed answer wrong
    if features.change_count >= 1:
        mistake_type = MISTAKE_TYPE_CHANGED_ANSWER_WRONG
    
    # Rule 2: Time pressure wrong
    elif features.remaining_sec_at_answer is not None and features.remaining_sec_at_answer <= time_pressure_remaining_sec:
        mistake_type = MISTAKE_TYPE_TIME_PRESSURE_WRONG
    
    # Rule 3: Fast wrong
    elif features.time_spent_sec is not None and features.time_spent_sec <= fast_wrong_sec:
        mistake_type = MISTAKE_TYPE_FAST_WRONG
    
    # Rule 4: Distracted wrong
    elif features.blur_count >= blur_threshold:
        mistake_type = MISTAKE_TYPE_DISTRACTED_WRONG
    
    # Rule 5: Slow wrong
    elif features.time_spent_sec is not None and features.time_spent_sec >= slow_wrong_sec:
        mistake_type = MISTAKE_TYPE_SLOW_WRONG
    
    # Rule 6: Knowledge gap (fallback)
    else:
        mistake_type = MISTAKE_TYPE_KNOWLEDGE_GAP
    
    # Add rule_fired to evidence
    evidence["rule_fired"] = mistake_type
    
    # Get severity
    severity = severity_rules.get(mistake_type, 2)  # Default severity 2
    
    return MistakeClassification(
        mistake_type=mistake_type,
        severity=severity,
        evidence=evidence,
    )


def classify_session_mistakes_v0(
    features_list: list[AttemptFeatures],
    params: dict[str, Any],
) -> list[tuple[AttemptFeatures, MistakeClassification]]:
    """
    Classify all wrong answers in a session.
    
    Args:
        features_list: List of extracted features for all attempts
        params: Algorithm parameters
    
    Returns:
        List of (features, classification) tuples for wrong answers only
    """
    results = []
    
    for features in features_list:
        classification = classify_mistake_v0(features, params)
        if classification is not None:
            results.append((features, classification))
    
    return results
