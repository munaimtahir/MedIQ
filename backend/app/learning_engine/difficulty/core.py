"""
Core Elo math for difficulty calibration.

Pure functions implementing:
- Probability model with guess floor
- Dynamic K computation based on uncertainty
- Uncertainty updates (decay + age)
- Rating updates

All functions are numerically stable and return finite values.
"""

import math
from datetime import datetime, timedelta
from typing import Tuple

from app.learning_engine.config import (
    ELO_GUESS_FLOOR,
    ELO_K_MAX,
    ELO_K_MIN,
    ELO_SCALE,
    ELO_UNC_AGE_INCREASE_PER_DAY,
    ELO_UNC_DECAY_PER_ATTEMPT,
    ELO_UNC_FLOOR,
)


def sigmoid(x: float) -> float:
    """
    Numerically stable sigmoid function.

    Args:
        x: Input value

    Returns:
        sigmoid(x) in [0, 1]
    """
    # Clamp input to prevent overflow
    x = max(-500.0, min(500.0, x))

    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    else:
        # For negative x, use exp(x) / (1 + exp(x)) to avoid overflow
        exp_x = math.exp(x)
        return exp_x / (1.0 + exp_x)


def p_correct(theta: float, b: float, guess_floor: float, scale: float) -> float:
    """
    Predict probability of correct answer with guess floor.

    Formula:
        p = g + (1 - g) * sigmoid((θ - b) / scale)

    Where:
        - g = guess_floor (e.g., 0.20 for 5-option MCQ)
        - θ = user ability
        - b = question difficulty
        - scale = Elo scale factor (typically 400)

    Args:
        theta: User ability rating
        b: Question difficulty rating
        guess_floor: Minimum probability (guessing)
        scale: Elo scale factor

    Returns:
        Probability of correct answer in [guess_floor, 1.0]
    """
    # Clamp inputs
    theta = max(-3000.0, min(3000.0, theta))
    b = max(-3000.0, min(3000.0, b))
    guess_floor = max(0.0, min(0.5, guess_floor))
    scale = max(1.0, scale)

    # Compute sigmoid component
    diff = (theta - b) / scale
    sig = sigmoid(diff)

    # Apply guess floor
    p = guess_floor + (1.0 - guess_floor) * sig

    # Final clamp
    return max(guess_floor, min(1.0, p))


def compute_delta(score: bool, p: float) -> float:
    """
    Compute prediction error.

    Args:
        score: Actual outcome (True = correct, False = incorrect)
        p: Predicted probability of correct

    Returns:
        Error: score - p
    """
    s = 1.0 if score else 0.0
    return s - p


def compute_dynamic_k(k_base: float, unc: float, k_min: float, k_max: float) -> float:
    """
    Compute uncertainty-aware dynamic K factor.

    K increases monotonically with uncertainty:
    - High uncertainty → large K (fast learning)
    - Low uncertainty → small K (stable rating)

    Formula:
        k_eff = k_min + (k_max - k_min) * (unc / (unc + k_base))

    This gives:
    - unc = 0 → k_eff = k_min
    - unc = k_base → k_eff = (k_min + k_max) / 2
    - unc → ∞ → k_eff = k_max

    Args:
        k_base: Base K value (reference uncertainty level)
        unc: Current uncertainty (RD-like)
        k_min: Minimum K (for mature ratings)
        k_max: Maximum K (for new ratings)

    Returns:
        Effective K factor in [k_min, k_max]
    """
    # Clamp inputs
    k_base = max(1.0, k_base)
    unc = max(0.0, unc)
    k_min = max(0.0, k_min)
    k_max = max(k_min, k_max)

    # Compute normalized uncertainty
    norm_unc = unc / (unc + k_base)

    # Linear interpolation
    k_eff = k_min + (k_max - k_min) * norm_unc

    # Final clamp
    return max(k_min, min(k_max, k_eff))


def update_uncertainty(
    unc: float,
    n_attempts: int,
    last_seen_at: datetime | None,
    now: datetime,
    unc_floor: float,
    unc_decay_per_attempt: float,
    unc_age_increase_per_day: float,
) -> float:
    """
    Update uncertainty based on attempts and inactivity.

    Two effects:
    1. Decay with attempts: unc *= decay_rate (geometric decay toward floor)
    2. Age increase: unc += days_inactive * age_rate

    Args:
        unc: Current uncertainty
        n_attempts: Number of attempts so far
        last_seen_at: Last activity timestamp (None if first attempt)
        now: Current timestamp
        unc_floor: Minimum uncertainty
        unc_decay_per_attempt: Multiplier per attempt (e.g., 0.9)
        unc_age_increase_per_day: Increase per day of inactivity

    Returns:
        Updated uncertainty >= unc_floor
    """
    # Clamp inputs
    unc = max(unc_floor, unc)
    unc_decay_per_attempt = max(0.5, min(1.0, unc_decay_per_attempt))
    unc_age_increase_per_day = max(0.0, unc_age_increase_per_day)

    # Apply decay from this attempt
    unc_after_decay = unc * unc_decay_per_attempt

    # Apply age increase if there was previous activity
    if last_seen_at is not None:
        days_inactive = (now - last_seen_at).total_seconds() / (24 * 3600)
        days_inactive = max(0.0, min(365.0, days_inactive))  # Cap at 1 year
        age_increase = days_inactive * unc_age_increase_per_day
        unc_after_decay += age_increase

    # Ensure floor
    return max(unc_floor, unc_after_decay)


def apply_update(
    theta: float, b: float, k_u: float, k_q: float, delta: float
) -> Tuple[float, float]:
    """
    Apply Elo rating updates.

    Updates:
        θ_new = θ + k_u * Δ
        b_new = b - k_q * Δ

    Note: Question difficulty decreases when user gets it correct (Δ > 0),
    making the question "easier" in the rating system.

    Args:
        theta: Current user ability
        b: Current question difficulty
        k_u: User K factor
        k_q: Question K factor
        delta: Prediction error (score - p_pred)

    Returns:
        Tuple of (theta_new, b_new)
    """
    # Clamp inputs
    theta = max(-3000.0, min(3000.0, theta))
    b = max(-3000.0, min(3000.0, b))
    k_u = max(0.0, k_u)
    k_q = max(0.0, k_q)
    delta = max(-1.0, min(1.0, delta))

    # Apply updates
    theta_new = theta + k_u * delta
    b_new = b - k_q * delta  # Note: minus sign for question difficulty

    # Clamp outputs
    theta_new = max(-3000.0, min(3000.0, theta_new))
    b_new = max(-3000.0, min(3000.0, b_new))

    return theta_new, b_new


def validate_rating_finite(rating: float, name: str = "rating") -> None:
    """
    Validate that a rating is finite (not NaN or Inf).

    Args:
        rating: Rating value to check
        name: Name for error message

    Raises:
        ValueError: If rating is not finite
    """
    if not math.isfinite(rating):
        raise ValueError(f"{name} is not finite: {rating}")


def clamp_rating(rating: float, min_val: float = -3000.0, max_val: float = 3000.0) -> float:
    """
    Clamp rating to valid range.

    Args:
        rating: Rating value
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Clamped rating
    """
    return max(min_val, min(max_val, rating))
