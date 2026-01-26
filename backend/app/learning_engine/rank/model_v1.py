"""Rank prediction v1: Empirical CDF over theta_proxy (quantile-based)."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.rank.cohort import cohort_key_for_user
from app.models.difficulty import DifficultyQuestionRating
from app.models.rank import RankPredictionSnapshot, RankSnapshotStatus
from app.models.user import User

logger = logging.getLogger(__name__)


async def compute_theta_proxy(
    db: AsyncSession,
    user_id: UUID,
    config: dict[str, Any],
) -> tuple[float | None, str]:
    """
    Compute theta_proxy (ability proxy) for a user.

    Priority (from config):
    1. Elo user rating (if exists)
    2. Mastery-weighted score
    3. Zero (with insufficient_data status)

    Args:
        db: Database session
        user_id: User ID
        config: Rank config dict

    Returns:
        Tuple of (theta_proxy, status)
        - theta_proxy: float or None
        - status: "ok" | "insufficient_data"
    """
    priority = config.get("THETA_PROXY_PRIORITY", ["elo_rating", "mastery_weighted", "zero"])

    for method in priority:
        if method == "elo_rating":
            # Try to get Elo rating (global or per-theme average)
            stmt = select(DifficultyQuestionRating).where(
                DifficultyQuestionRating.scope_type == "GLOBAL",
                DifficultyQuestionRating.scope_id.is_(None),
            )
            result = await db.execute(stmt)
            ratings = result.scalars().all()

            if ratings:
                # Use average rating as proxy (or could use user-specific if available)
                # For now, we'll need user-specific Elo if it exists
                # TODO: Add user-specific Elo rating table or use mastery-weighted
                pass

        elif method == "mastery_weighted":
            # Get mastery scores from canonical state
            from app.models.algo_runtime import UserMasteryState

            stmt = select(UserMasteryState).where(UserMasteryState.user_id == user_id)
            result = await db.execute(stmt)
            mastery_states = result.scalars().all()

            if mastery_states:
                total_weight = 0.0
                weighted_sum = 0.0

                for state in mastery_states:
                    if state.mastery_score is not None:
                        # Use attempts_total as weight (from user_theme_stats)
                        from app.models.algo_runtime import UserThemeStats

                        stats_stmt = select(UserThemeStats).where(
                            UserThemeStats.user_id == user_id,
                            UserThemeStats.theme_id == state.theme_id,
                        )
                        stats_result = await db.execute(stats_stmt)
                        stats = stats_result.scalar_one_or_none()

                        weight = stats.attempts_total if stats else 1
                        weighted_sum += state.mastery_score * weight
                        total_weight += weight

                if total_weight > 0:
                    theta_proxy = weighted_sum / total_weight
                    # Normalize to reasonable range (e.g., -3 to 3)
                    # Mastery is 0..1, map to -3..3
                    theta_proxy = (theta_proxy - 0.5) * 6
                    return theta_proxy, "ok"

        elif method == "zero":
            return 0.0, "insufficient_data"

    # Fallback
    return None, "insufficient_data"


async def compute_cohort_cdf(
    db: AsyncSession,
    cohort_key: str,
    config: dict[str, Any],
    window_days: int | None = None,
) -> dict[str, Any]:
    """
    Compute empirical CDF for a cohort.

    Args:
        db: Database session
        cohort_key: Cohort key (e.g., "year:1")
        config: Rank config dict
        window_days: Optional window override

    Returns:
        Dictionary with:
        - thetas: list of theta_proxy values
        - n_users: number of users
        - cdf_data: sorted (theta, cumulative_fraction) pairs
    """
    window_days = window_days or config.get("WINDOW_DAYS_COHORT_STATS", 90)
    min_cohort_n = config.get("MIN_COHORT_N", 50)

    # Parse cohort_key
    parts = cohort_key.split(":")
    year_id = None
    if len(parts) >= 2 and parts[0] == "year":
        try:
            year_id = int(parts[1])
        except ValueError:
            pass

    # Get users in cohort
    from app.models.academic import UserProfile

    stmt = select(User.id, UserProfile.user_id).join(
        UserProfile, User.id == UserProfile.user_id
    )
    if year_id:
        stmt = stmt.where(UserProfile.selected_year_id == year_id)

    result = await db.execute(stmt)
    user_rows = result.all()

    # Compute theta_proxy for each user
    thetas: list[float] = []
    user_ids: list[UUID] = []

    for row in user_rows:
        user_id = row[0]
        theta, status = await compute_theta_proxy(db, user_id, config)
        if status == "ok" and theta is not None:
            thetas.append(theta)
            user_ids.append(user_id)

    if len(thetas) < min_cohort_n:
        return {
            "thetas": thetas,
            "n_users": len(thetas),
            "cdf_data": [],
            "status": "insufficient_data",
        }

    # Build empirical CDF
    thetas_sorted = sorted(thetas)
    n = len(thetas_sorted)
    cdf_data = [(theta, (i + 1) / n) for i, theta in enumerate(thetas_sorted)]

    return {
        "thetas": thetas,
        "n_users": n,
        "cdf_data": cdf_data,
        "status": "ok",
    }


def percentile_from_cdf(theta: float, cdf_data: list[tuple[float, float]]) -> float:
    """
    Get percentile from CDF data.

    Args:
        theta: User's theta_proxy
        cdf_data: Sorted list of (theta, cumulative_fraction) pairs

    Returns:
        Percentile (0..1)
    """
    if not cdf_data:
        return 0.5  # Neutral if no data

    # Binary search or linear interpolation
    for i, (t, p) in enumerate(cdf_data):
        if theta <= t:
            if i == 0:
                return 0.0
            # Interpolate between previous and current
            prev_t, prev_p = cdf_data[i - 1]
            if t == prev_t:
                return prev_p
            # Linear interpolation
            ratio = (theta - prev_t) / (t - prev_t)
            return prev_p + ratio * (p - prev_p)

    # Above max
    return 1.0


def compute_uncertainty_band(
    percentile: float,
    cohort_n: int,
    config: dict[str, Any],
) -> tuple[float, float]:
    """
    Compute uncertainty band for percentile.

    Args:
        percentile: Predicted percentile (0..1)
        cohort_n: Cohort size
        config: Rank config dict

    Returns:
        Tuple of (band_low, band_high)
    """
    z = config.get("RANK_BAND_Z", 1.28)  # ~80% confidence

    # Analytic approximation: sqrt(p*(1-p)/N) * Z
    p = max(0.01, min(0.99, percentile))  # Clip to avoid division issues
    std_err = np.sqrt(p * (1 - p) / cohort_n)
    half_width = z * std_err

    band_low = max(0.0, percentile - half_width)
    band_high = min(1.0, percentile + half_width)

    return float(band_low), float(band_high)


async def compute_rank_snapshot(
    db: AsyncSession,
    user_id: UUID,
    cohort_key: str | None = None,
    config: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> RankPredictionSnapshot | None:
    """
    Compute rank prediction snapshot for a user.

    Args:
        db: Database session
        user_id: User ID
        cohort_key: Optional cohort key (auto-generated if None)
        config: Optional rank config (fetched if None)
        now: Optional timestamp (uses current time if None)

    Returns:
        RankPredictionSnapshot or None if disabled/blocked
    """
    from app.learning_engine.runtime import is_safe_mode_freeze_updates
    from app.learning_engine.rank.config import get_rank_config

    # Check freeze mode
    if await is_safe_mode_freeze_updates(db):
        logger.warning(f"Rank snapshot blocked for user {user_id}: freeze_updates is enabled")
        snapshot = RankPredictionSnapshot(
            user_id=user_id,
            cohort_key=cohort_key or await cohort_key_for_user(db, str(user_id)),
            status=RankSnapshotStatus.BLOCKED_FROZEN,
            model_version="rank_v1_empirical_cdf",
            computed_at=now or datetime.now(timezone.utc),
        )
        return snapshot

    # Get config
    if config is None:
        config_data = await get_rank_config(db)
        if not config_data:
            logger.warning("Rank config not found, using defaults")
            config = {}
        else:
            config = config_data.get("config_json", {})

    # Get cohort key
    if cohort_key is None:
        cohort_key = await cohort_key_for_user(db, str(user_id))

    # Compute theta_proxy
    theta_proxy, theta_status = await compute_theta_proxy(db, user_id, config)

    if theta_status == "insufficient_data" or theta_proxy is None:
        snapshot = RankPredictionSnapshot(
            user_id=user_id,
            cohort_key=cohort_key,
            theta_proxy=None,
            status=RankSnapshotStatus.INSUFFICIENT_DATA,
            model_version="rank_v1_empirical_cdf",
            computed_at=now or datetime.now(timezone.utc),
        )
        return snapshot

    # Compute cohort CDF
    cohort_data = await compute_cohort_cdf(db, cohort_key, config)

    if cohort_data["status"] != "ok":
        snapshot = RankPredictionSnapshot(
            user_id=user_id,
            cohort_key=cohort_key,
            theta_proxy=theta_proxy,
            status=RankSnapshotStatus.INSUFFICIENT_DATA,
            model_version="rank_v1_empirical_cdf",
            computed_at=now or datetime.now(timezone.utc),
        )
        return snapshot

    # Get percentile
    percentile = percentile_from_cdf(theta_proxy, cohort_data["cdf_data"])

    # Compute uncertainty band
    band_low, band_high = compute_uncertainty_band(
        percentile,
        cohort_data["n_users"],
        config,
    )

    # Compute features hash (for reproducibility)
    features = {
        "theta_proxy": round(theta_proxy, 4),
        "cohort_key": cohort_key,
        "cohort_n": cohort_data["n_users"],
    }
    features_json = json.dumps(features, sort_keys=True)
    features_hash = hashlib.sha256(features_json.encode()).hexdigest()[:16]

    snapshot = RankPredictionSnapshot(
        user_id=user_id,
        cohort_key=cohort_key,
        theta_proxy=theta_proxy,
        predicted_percentile=percentile,
        band_low=band_low,
        band_high=band_high,
        status=RankSnapshotStatus.OK,
        model_version="rank_v1_empirical_cdf",
        features_hash=features_hash,
        computed_at=now or datetime.now(timezone.utc),
    )

    return snapshot
