"""ALGO_BRIDGE_SPEC_v1 - Config-driven mapping functions.

All functions are pure, deterministic, and idempotent.
All parameters come from algo_bridge_config.config_json.
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Mastery Bridging
# ============================================================================


def compute_v0_mastery_from_aggregates(
    attempts_total: int,
    correct_total: int,
    last_attempt_at: datetime | None,
    now: datetime,
    cfg: dict[str, Any],
) -> float:
    """
    Compute v0 mastery score from aggregates (ALGO_BRIDGE_SPEC_v1).

    Args:
        attempts_total: Total attempts
        correct_total: Total correct attempts
        last_attempt_at: Last attempt timestamp (or None)
        now: Current timestamp
        cfg: Bridge config (from algo_bridge_config.config_json)

    Returns:
        mastery_score (float 0..1)
    """
    floor = cfg.get("MASTERY_FLOOR", 0.01)
    ceil = cfg.get("MASTERY_CEIL", 0.99)
    min_attempts = cfg.get("MASTERY_MIN_ATTEMPTS_FOR_CONFIDENCE", 10)
    tau_days = cfg.get("MASTERY_RECENCY_TAU_DAYS", 21)

    # Not enough data
    if attempts_total < min_attempts:
        return 0.5  # Neutral

    # Compute accuracy
    p = correct_total / attempts_total if attempts_total > 0 else 0.5

    # Compute recency
    if last_attempt_at:
        delta_days = (now - last_attempt_at.replace(tzinfo=timezone.utc)).total_seconds() / 86400
        r = math.exp(-delta_days / tau_days)
    else:
        r = 0.0  # No recent attempts

    # Compute raw mastery
    mastery_raw = r * p + (1 - r) * 0.5

    # Clip to bounds
    mastery_score = max(floor, min(ceil, mastery_raw))

    return mastery_score


def init_bkt_from_mastery(
    mastery_score: float,
    p_prior: float,
    attempts_total: int,
    cfg: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    """
    Initialize BKT from mastery_score (ALGO_BRIDGE_SPEC_v1).

    Args:
        mastery_score: Canonical mastery score (0..1)
        p_prior: BKT prior probability (default prior)
        attempts_total: Total attempts for this theme
        cfg: Bridge config

    Returns:
        (bkt_p_mastered, bkt_state_json)
    """
    mode = cfg.get("BKT_INIT_PRIOR_FROM_MASTERY", "direct")
    shrink_alpha = cfg.get("BKT_PRIOR_SHRINK_ALPHA", 0.15)
    min_obs = cfg.get("BKT_MIN_OBS_FOR_STRONG_INIT", 20)

    if mode == "direct":
        # Direct mapping with bounds
        bkt_p_mastered = max(0.1, min(0.9, mastery_score))
        bkt_state_json = {
            "p_L0": bkt_p_mastered,
            "n_attempts": attempts_total,
            "initialized_from_mastery": True,
        }
    elif mode == "shrink_to_prior":
        # Shrinkage toward prior
        if attempts_total >= min_obs:
            # Strong initialization (less shrinkage)
            effective_alpha = shrink_alpha * 0.5
        else:
            effective_alpha = shrink_alpha

        bkt_p_mastered = (1 - effective_alpha) * mastery_score + effective_alpha * p_prior
        bkt_p_mastered = max(0.1, min(0.9, bkt_p_mastered))  # Bound

        bkt_state_json = {
            "p_L0": bkt_p_mastered,
            "n_attempts": attempts_total,
            "shrinkage_alpha": effective_alpha,
            "initialized_from_mastery": True,
        }
    else:
        # Fallback to direct
        logger.warning(f"Unknown BKT init mode: {mode}, using direct")
        bkt_p_mastered = max(0.1, min(0.9, mastery_score))
        bkt_state_json = {
            "p_L0": bkt_p_mastered,
            "n_attempts": attempts_total,
            "initialized_from_mastery": True,
        }

    return bkt_p_mastered, bkt_state_json


# ============================================================================
# Revision Bridging
# ============================================================================


def nearest_bin(days: int, bins: list[int]) -> int:
    """
    Find nearest bin value for given days.
    
    When there's a tie, prefers the larger bin (rounds up).

    Args:
        days: Number of days
        bins: List of bin values (sorted)

    Returns:
        Nearest bin value
    """
    if not bins:
        return max(1, days)

    # Find closest bin, preferring larger when tied
    closest = bins[0]
    min_diff = abs(days - closest)

    # Iterate forward, but on ties prefer the later (larger) bin
    for bin_val in bins:
        diff = abs(days - bin_val)
        if diff < min_diff or (diff == min_diff and bin_val > closest):
            min_diff = diff
            closest = bin_val

    return closest


def stage_from_interval(interval_days: int, bins: list[int], stage_max: int) -> int:
    """
    Compute stage from interval days.
    
    Maps interval to stage based on the largest bin that is < interval_days.
    If interval_days equals a bin, uses that bin's stage.

    Args:
        interval_days: Interval in days
        bins: List of bin values (sorted)
        stage_max: Maximum stage number

    Returns:
        Stage number (1..stage_max)
    """
    if not bins:
        return 1

    # Find the largest bin that is <= interval_days
    # Special case: if interval equals a bin exactly, use that bin's stage
    for i, bin_val in enumerate(bins):
        if interval_days == bin_val:
            return min(i + 1, stage_max)
        if interval_days < bin_val:
            # Use previous bin's stage (or stage 1 if first bin)
            return min(max(1, i), stage_max)

    # Beyond all bins
    return stage_max


def v1_to_v0_revision_bridge(
    user_revision_state: dict[str, Any],
    user_theme_stats: dict[str, Any] | None,
    cfg: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """
    Bridge v1 revision state to v0 (ALGO_BRIDGE_SPEC_v1).

    Preserves due_at unless invalid.

    Args:
        user_revision_state: Current revision state dict
        user_theme_stats: Theme stats dict (or None)
        cfg: Bridge config
        now: Current timestamp

    Returns:
        Updated revision state dict (with v0 fields populated)
    """
    bins = cfg.get("V0_INTERVAL_BINS_DAYS", [1, 3, 7, 14, 30, 60, 120])
    stage_max = cfg.get("V0_STAGE_MAX", 6)
    preservation_mode = cfg.get("DUE_AT_PRESERVATION_MODE", "preserve")

    # Copy state
    updated = user_revision_state.copy()

    # Normalize datetime objects
    due_at = user_revision_state.get("due_at")
    if due_at:
        if isinstance(due_at, str):
            due_at = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        elif due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        updated["due_at"] = due_at

    last_review_at = user_revision_state.get("last_review_at")
    if last_review_at:
        if isinstance(last_review_at, str):
            last_review_at = datetime.fromisoformat(last_review_at.replace("Z", "+00:00"))
        elif last_review_at.tzinfo is None:
            last_review_at = last_review_at.replace(tzinfo=timezone.utc)
        updated["last_review_at"] = last_review_at

    # Compute v0_interval_days if missing
    if updated.get("v0_interval_days") is None:
        interval_days = None

        if due_at and last_review_at:
            # Use time between last review and due date
            delta = (due_at - last_review_at).total_seconds() / 86400
            interval_days = max(1, int(delta))
        elif due_at:
            # Use time until due date
            delta = (due_at - now).total_seconds() / 86400
            interval_days = max(1, int(delta))
        elif user_theme_stats and user_theme_stats.get("last_attempt_at"):
            # Use time since last attempt
            last_attempt = user_theme_stats["last_attempt_at"]
            if isinstance(last_attempt, str):
                last_attempt = datetime.fromisoformat(last_attempt.replace("Z", "+00:00"))
            elif isinstance(last_attempt, datetime):
                if last_attempt.tzinfo is None:
                    last_attempt = last_attempt.replace(tzinfo=timezone.utc)

            delta = (now - last_attempt).total_seconds() / 86400
            interval_days = max(1, int(delta))
        else:
            interval_days = 1  # Default

        # Bin to nearest
        updated["v0_interval_days"] = nearest_bin(interval_days, bins)

    # Compute v0_stage if missing
    if updated.get("v0_stage") is None:
        interval = updated.get("v0_interval_days", 1)
        updated["v0_stage"] = stage_from_interval(interval, bins, stage_max)

    return updated


def v0_to_v1_revision_bridge(
    user_revision_state: dict[str, Any],
    user_theme_stats: dict[str, Any] | None,
    cfg: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """
    Bridge v0 revision state to v1 (ALGO_BRIDGE_SPEC_v1).

    Preserves due_at unless invalid.

    Args:
        user_revision_state: Current revision state dict
        user_theme_stats: Theme stats dict (or None)
        cfg: Bridge config
        now: Current timestamp

    Returns:
        Updated revision state dict (with FSRS fields populated)
    """
    bins = cfg.get("V0_INTERVAL_BINS_DAYS", [1, 3, 7, 14, 30, 60, 120])
    stability_mode = cfg.get("FSRS_STABILITY_FROM_INTERVAL_MODE", "monotonic_log")
    difficulty_mode = cfg.get("FSRS_DIFFICULTY_FROM_ERROR_RATE_MODE", "linear_clip")
    difficulty_min = cfg.get("FSRS_DIFFICULTY_MIN", 0.05)
    difficulty_max = cfg.get("FSRS_DIFFICULTY_MAX", 0.95)

    # Copy state
    updated = user_revision_state.copy()

    # Normalize datetime objects
    due_at = user_revision_state.get("due_at")
    if due_at:
        if isinstance(due_at, str):
            due_at = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        elif due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        updated["due_at"] = due_at

    last_review_at = user_revision_state.get("last_review_at")
    if last_review_at:
        if isinstance(last_review_at, str):
            last_review_at = datetime.fromisoformat(last_review_at.replace("Z", "+00:00"))
        elif last_review_at.tzinfo is None:
            last_review_at = last_review_at.replace(tzinfo=timezone.utc)
        updated["last_review_at"] = last_review_at

    # Compute stability from v0_interval_days if missing
    if updated.get("stability") is None and updated.get("v0_interval_days") is not None:
        interval = updated["v0_interval_days"]
        i_max = max(bins) if bins else 30

        if stability_mode == "monotonic_log":
            # Log mapping
            stability = math.log(1 + interval) * (i_max / math.log(1 + i_max))
        elif stability_mode == "linear":
            # Linear mapping
            stability = interval * (i_max / max(bins)) if bins else interval
        elif stability_mode == "sqrt":
            # Square root mapping
            stability = math.sqrt(interval) * (i_max / math.sqrt(max(bins))) if bins else math.sqrt(interval)
        else:
            # Fallback to log
            stability = math.log(1 + interval) * (i_max / math.log(1 + i_max))

        # Clip to reasonable bounds
        stability = max(1.0, min(365.0, stability))
        updated["stability"] = stability

    # Compute difficulty from error rate if missing
    if updated.get("difficulty") is None and user_theme_stats:
        attempts_total = user_theme_stats.get("attempts_total", 0)
        correct_total = user_theme_stats.get("correct_total", 0)

        if attempts_total > 0:
            err_rate = 1.0 - (correct_total / attempts_total)
        else:
            err_rate = 0.5  # Neutral

        if difficulty_mode == "linear_clip":
            difficulty = max(difficulty_min, min(difficulty_max, err_rate))
        elif difficulty_mode == "sigmoid":
            # Sigmoid mapping
            sigmoid = 1 / (1 + math.exp(-10 * (err_rate - 0.5)))
            difficulty = sigmoid * (difficulty_max - difficulty_min) + difficulty_min
        else:
            # Fallback to linear clip
            difficulty = max(difficulty_min, min(difficulty_max, err_rate))

        updated["difficulty"] = difficulty

    # Set due_at if missing and v0_interval_days exists
    if updated.get("due_at") is None and updated.get("v0_interval_days") is not None:
        interval = updated["v0_interval_days"]
        updated["due_at"] = now + timedelta(days=interval)

    return updated


# ============================================================================
# Bandit Initialization
# ============================================================================


def init_bandit_beta_from_mastery(
    mastery_score: float,
    attempts_total: int,
    cfg: dict[str, Any],
) -> tuple[float, float]:
    """
    Initialize Beta prior from mastery_score (ALGO_BRIDGE_SPEC_v1).

    Args:
        mastery_score: Canonical mastery score (0..1)
        attempts_total: Total attempts
        cfg: Bridge config

    Returns:
        (alpha, beta) tuple
    """
    strength_min = cfg.get("BANDIT_PRIOR_STRENGTH_MIN", 5)
    strength_max = cfg.get("BANDIT_PRIOR_STRENGTH_MAX", 50)

    # Compute strength
    S = max(strength_min, min(strength_max, attempts_total))

    # Compute alpha and beta
    alpha = 1.0 + mastery_score * S
    beta = 1.0 + (1.0 - mastery_score) * S

    return alpha, beta
