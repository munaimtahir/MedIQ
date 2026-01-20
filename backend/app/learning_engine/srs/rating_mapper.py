"""
Rating mapper - converts MCQ attempts to FSRS ratings (1-4).

FSRS Ratings:
- 1 (Again): Failed to recall
- 2 (Hard): Recalled with difficulty
- 3 (Good): Recalled correctly
- 4 (Easy): Recalled easily and quickly

Mapping Rules:
- Incorrect answer -> 1 (Again)
- Correct but slow OR many changes -> 2 (Hard)
- Correct -> 3 (Good)
- Correct, fast, confident -> 4 (Easy)
"""

import logging
from typing import Optional, Tuple

from app.learning_engine.config import (
    RATING_FAST_ANSWER_MS,
    RATING_SLOW_ANSWER_MS,
    RATING_MAX_CHANGES_FOR_CONFIDENT,
    TELEMETRY_MAX_TIME_MS,
    TELEMETRY_MIN_TIME_MS,
    TELEMETRY_MAX_CHANGES,
)

logger = logging.getLogger(__name__)


def map_attempt_to_rating(
    correct: bool,
    time_spent_ms: Optional[int] = None,
    change_count: Optional[int] = None,
    marked_for_review: bool = False,
) -> int:
    """
    Map an MCQ attempt to an FSRS rating (1-4).

    Deterministic mapping based on:
    - Correctness
    - Time spent
    - Answer changes
    - Mark for review flag

    Args:
        correct: Whether the answer was correct
        time_spent_ms: Time spent on question (milliseconds)
        change_count: Number of times answer was changed
        marked_for_review: Whether student marked question for review

    Returns:
        FSRS rating: 1 (Again), 2 (Hard), 3 (Good), or 4 (Easy)
    """
    # Rule 1: Incorrect -> Always "Again" (1)
    if not correct:
        return 1  # Again

    # For correct answers, determine difficulty level

    # Rule 2: Marked for review -> "Hard" (2)
    # Student flagged uncertainty even though they got it right
    if marked_for_review:
        return 2  # Hard

    # Rule 3: Many answer changes -> "Hard" (2)
    # Multiple changes indicate uncertainty
    if change_count is not None and change_count > RATING_MAX_CHANGES_FOR_CONFIDENT.value:
        return 2  # Hard

    # Rule 4: Very slow answer -> "Hard" (2)
    # Taking too long indicates struggle even if correct
    if time_spent_ms is not None and time_spent_ms > RATING_SLOW_ANSWER_MS.value:
        return 2  # Hard

    # Rule 5: Fast and confident -> "Easy" (4)
    # Quick answer with no changes indicates mastery
    if (
        time_spent_ms is not None
        and time_spent_ms < RATING_FAST_ANSWER_MS.value
        and (change_count is None or change_count == 0)
    ):
        return 4  # Easy

    # Rule 6: Default for correct answers -> "Good" (3)
    # Answered correctly without clear signs of difficulty or ease
    return 3  # Good


def explain_rating(
    rating: int,
    correct: bool,
    time_spent_ms: Optional[int] = None,
    change_count: Optional[int] = None,
    marked_for_review: bool = False,
) -> str:
    """
    Explain why a particular rating was assigned.

    Useful for debugging and user feedback.

    Args:
        rating: The assigned FSRS rating
        correct: Whether the answer was correct
        time_spent_ms: Time spent on question (ms)
        change_count: Number of answer changes
        marked_for_review: Whether marked for review

    Returns:
        Human-readable explanation string
    """
    if rating == 1:
        return "Incorrect answer (Again)"

    if rating == 2:
        reasons = []
        if marked_for_review:
            reasons.append("marked for review")
        if change_count is not None and change_count > 0:
            reasons.append(f"{change_count} answer changes")
        if time_spent_ms is not None and time_spent_ms > RATING_SLOW_ANSWER_MS.value:
            reasons.append(f"slow ({time_spent_ms/1000:.0f}s)")

        if reasons:
            return f"Correct but with difficulty: {', '.join(reasons)} (Hard)"
        return "Correct but uncertain (Hard)"

    if rating == 4:
        return f"Correct, fast ({time_spent_ms/1000 if time_spent_ms else '?'}s), confident (Easy)"

    # rating == 3
    return "Correct answer (Good)"


def get_rating_thresholds() -> dict:
    """
    Get current rating classification thresholds.

    Useful for configuration and testing.

    Returns:
        Dict of threshold values
    """
    return {
        "fast_answer_ms": RATING_FAST_ANSWER_MS.value,
        "slow_answer_ms": RATING_SLOW_ANSWER_MS.value,
        "max_changes_for_confident": RATING_MAX_CHANGES_FOR_CONFIDENT.value,
    }


def validate_telemetry(
    time_spent_ms: Optional[int],
    change_count: Optional[int],
) -> Tuple[Optional[int], Optional[int], list[str]]:
    """
    Validate and sanitize telemetry data.

    Args:
        time_spent_ms: Time spent (ms)
        change_count: Answer changes

    Returns:
        Tuple of (cleaned_time_ms, cleaned_changes, warnings)
    """
    warnings = []

    # Validate time_spent_ms
    if time_spent_ms is not None:
        if time_spent_ms < 0:
            warnings.append(f"Negative time_spent_ms: {time_spent_ms}")
            time_spent_ms = None
        elif time_spent_ms > TELEMETRY_MAX_TIME_MS.value:
            warnings.append(f"Suspiciously long time_spent_ms: {time_spent_ms}")
            # Keep it but flag
        elif time_spent_ms < TELEMETRY_MIN_TIME_MS.value:
            warnings.append(f"Suspiciously short time_spent_ms: {time_spent_ms}")
            # Keep it but flag

    # Validate change_count
    if change_count is not None:
        if change_count < 0:
            warnings.append(f"Negative change_count: {change_count}")
            change_count = 0
        elif change_count > TELEMETRY_MAX_CHANGES.value:
            warnings.append(f"Suspiciously high change_count: {change_count}")
            # Cap at max
            change_count = TELEMETRY_MAX_CHANGES.value

    return time_spent_ms, change_count, warnings


# Note: set_rating_thresholds() has been removed.
# Thresholds are now managed centrally in config.py
# To override thresholds, update the SourcedValue constants in config.py
# This ensures all threshold changes are documented with provenance.
