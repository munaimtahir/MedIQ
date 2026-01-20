"""
FSRS adapter - wraps the py-fsrs library for our use case.

Provides:
- Default FSRS-6 parameters
- State computation from review logs
- Next review scheduling
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fsrs import FSRS, Card, Rating, ReviewLog

from app.learning_engine.config import (
    FSRS_DEFAULT_WEIGHTS,
    FSRS_DESIRED_RETENTION,
    FSRS_RETENTION_MIN,
    FSRS_RETENTION_MAX,
)

logger = logging.getLogger(__name__)


def get_default_parameters(fsrs_version: str = "fsrs-6") -> dict:
    """
    Get default FSRS parameters.

    Args:
        fsrs_version: FSRS version string (currently only "fsrs-6" supported)

    Returns:
        Dict with 'weights' and 'desired_retention'
    """
    if fsrs_version != "fsrs-6":
        logger.warning(f"Unknown FSRS version '{fsrs_version}', using fsrs-6 defaults")

    return {
        "weights": FSRS_DEFAULT_WEIGHTS.value,
        "desired_retention": FSRS_DESIRED_RETENTION.value,
    }


def compute_next_state_and_due(
    current_stability: Optional[float],
    current_difficulty: Optional[float],
    rating: int,
    delta_days: float,
    weights: Optional[list[float]],
    desired_retention: float,
    reviewed_at: datetime,
) -> Tuple[float, float, datetime, float]:
    """
    Compute next FSRS state and due date after a review.

    Args:
        current_stability: Current stability (days), None for first review
        current_difficulty: Current difficulty [0, 10], None for first review
        rating: FSRS rating 1-4 (Again, Hard, Good, Easy)
        delta_days: Days since last review (0 for first review)
        weights: FSRS weights (19 params), None for defaults
        desired_retention: Target retention probability
        reviewed_at: Timestamp of this review

    Returns:
        Tuple of (new_stability, new_difficulty, due_at, retrievability)
    """
    # Validate rating
    if rating not in [1, 2, 3, 4]:
        raise ValueError(f"Invalid FSRS rating: {rating}. Must be 1-4.")

    # Use default weights if not provided
    if weights is None:
        weights = FSRS_DEFAULT_WEIGHTS.value

    # Validate weights length
    if len(weights) != 19:
        raise ValueError(f"FSRS-6 requires 19 weights, got {len(weights)}")

    # Create FSRS scheduler
    scheduler = FSRS(w=weights, request_retention=desired_retention)

    # Create Card object
    if current_stability is None or current_difficulty is None:
        # First review - create new card
        card = Card()
    else:
        # Existing card - set current state
        card = Card()
        card.stability = current_stability
        card.difficulty = current_difficulty
        card.last_review = reviewed_at - timedelta(days=delta_days)
        card.due = reviewed_at  # Currently due (being reviewed now)

    # Convert rating to FSRS Rating enum
    rating_map = {
        1: Rating.Again,
        2: Rating.Hard,
        3: Rating.Good,
        4: Rating.Easy,
    }
    fsrs_rating = rating_map[rating]

    # Compute retrievability at review time
    if current_stability is not None and delta_days > 0:
        retrievability = scheduler.forgetting_curve(
            elapsed_days=delta_days, stability=current_stability
        )
    else:
        retrievability = 1.0  # First review or immediate review

    # Schedule next review
    scheduled_card = scheduler.repeat(card, reviewed_at)[fsrs_rating]

    # Extract new state
    new_stability = scheduled_card.card.stability
    new_difficulty = scheduled_card.card.difficulty
    new_due_at = scheduled_card.card.due

    # Validate outputs (numerical stability checks)
    if not math.isfinite(new_stability) or new_stability <= 0:
        logger.warning(f"Invalid stability computed: {new_stability}. Using fallback.")
        new_stability = max(0.1, current_stability or 1.0)

    if not math.isfinite(new_difficulty) or new_difficulty < 0 or new_difficulty > 10:
        logger.warning(f"Invalid difficulty computed: {new_difficulty}. Using fallback.")
        new_difficulty = max(0, min(10, current_difficulty or 5.0))

    if not isinstance(new_due_at, datetime):
        logger.warning(f"Invalid due_at computed: {new_due_at}. Using fallback.")
        new_due_at = reviewed_at + timedelta(days=new_stability)

    # Ensure due_at is in the future
    if new_due_at <= reviewed_at:
        new_due_at = reviewed_at + timedelta(days=max(0.1, new_stability * 0.1))

    return new_stability, new_difficulty, new_due_at, retrievability


def create_review_log_from_state(
    user_id: str,
    concept_id: str,
    rating: int,
    reviewed_at: datetime,
    delta_days: float,
    predicted_retrievability: Optional[float] = None,
) -> ReviewLog:
    """
    Create an FSRS ReviewLog object for training.

    Args:
        user_id: User identifier
        concept_id: Concept identifier
        rating: FSRS rating 1-4
        reviewed_at: Review timestamp
        delta_days: Days since last review
        predicted_retrievability: Optional predicted retrievability

    Returns:
        FSRS ReviewLog object
    """
    rating_map = {
        1: Rating.Again,
        2: Rating.Hard,
        3: Rating.Good,
        4: Rating.Easy,
    }

    return ReviewLog(
        rating=rating_map[rating],
        elapsed_days=int(delta_days),  # FSRS expects integer days
        scheduled_days=0,  # Not used for training
        review=reviewed_at,
    )


def validate_weights(weights: list[float]) -> Tuple[bool, str]:
    """
    Validate FSRS weights.

    Args:
        weights: List of 19 FSRS-6 weights

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(weights) != 19:
        return False, f"Expected 19 weights, got {len(weights)}"

    for i, w in enumerate(weights):
        if not math.isfinite(w):
            return False, f"Weight {i} is not finite: {w}"

    # Check for reasonable ranges (very loose bounds)
    for i, w in enumerate(weights):
        if w < -10 or w > 100:
            return False, f"Weight {i} out of reasonable range: {w}"

    return True, ""


def compute_optimal_retention(
    review_logs: list[ReviewLog],
    weights: list[float],
    max_retention: Optional[float] = None,
    min_retention: Optional[float] = None,
) -> float:
    """
    Compute optimal retention target for a user.

    This is a simplified version - in production you'd want to consider:
    - Time available for reviews
    - Cost of reviews vs failures
    - User preferences

    For now, we'll use a heuristic based on review frequency.

    Args:
        review_logs: List of review logs
        weights: FSRS weights
        max_retention: Maximum retention target
        min_retention: Minimum retention target

    Returns:
        Optimal retention probability
    """
    # Use configured defaults if not provided
    if max_retention is None:
        max_retention = FSRS_RETENTION_MAX.value
    if min_retention is None:
        min_retention = FSRS_RETENTION_MIN.value

    if len(review_logs) < 10:
        return FSRS_DESIRED_RETENTION.value

    # Count reviews by rating
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for log in review_logs:
        if log.rating == Rating.Again:
            rating_counts[1] += 1
        elif log.rating == Rating.Hard:
            rating_counts[2] += 1
        elif log.rating == Rating.Good:
            rating_counts[3] += 1
        elif log.rating == Rating.Easy:
            rating_counts[4] += 1

    total = sum(rating_counts.values())
    if total == 0:
        return DEFAULT_DESIRED_RETENTION

    # If user is struggling (many Again/Hard), lower retention target
    struggle_rate = (rating_counts[1] + rating_counts[2]) / total

    if struggle_rate > 0.4:
        # User struggling - lower retention to reduce review burden
        optimal = min_retention
    elif struggle_rate < 0.15:
        # User doing well - can increase retention
        optimal = max_retention
    else:
        # Interpolate based on struggle rate
        # struggle_rate in [0.15, 0.4] maps to retention in [max, min]
        t = (struggle_rate - 0.15) / (0.4 - 0.15)
        optimal = max_retention - t * (max_retention - min_retention)

    return round(optimal, 2)
