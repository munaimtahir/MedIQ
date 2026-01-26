"""Rank activation eligibility gates."""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.rank.config import get_rank_config
from app.models.rank import RankPredictionSnapshot, RankSnapshotStatus

logger = logging.getLogger(__name__)


async def is_rank_eligible_for_activation(
    db: AsyncSession, cohort_key: str
) -> tuple[bool, list[str]]:
    """
    Check if rank is eligible for activation for a cohort.

    Gates:
    1. MIN_COHORT_N: Sufficient users with ok status
    2. Stability: Median absolute percentile change <= threshold
    3. Coverage: % users with ok status >= threshold

    Args:
        db: Database session
        cohort_key: Cohort key to check

    Returns:
        Tuple of (eligible, reasons)
        - eligible: bool
        - reasons: list of gate failure reasons
    """
    config_data = await get_rank_config(db)
    if not config_data:
        return False, ["Rank config not found"]

    config = config_data.get("config_json", {})

    min_cohort_n = config.get("ACTIVATION_MIN_COHORT_N", 100)
    stability_threshold = config.get("STABILITY_THRESHOLD_ABS_CHANGE", 0.05)
    coverage_threshold = config.get("COVERAGE_THRESHOLD", 0.80)

    reasons: list[str] = []

    # Get recent snapshots for cohort
    stmt = (
        select(RankPredictionSnapshot)
        .where(RankPredictionSnapshot.cohort_key == cohort_key)
        .order_by(RankPredictionSnapshot.computed_at.desc())
        .limit(1000)  # Last 1000 snapshots
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    if not snapshots:
        return False, ["No snapshots found for cohort"]

    # Gate 1: Coverage
    ok_snapshots = [s for s in snapshots if s.status == RankSnapshotStatus.OK]
    total_snapshots = len(snapshots)
    coverage = len(ok_snapshots) / total_snapshots if total_snapshots > 0 else 0.0

    if coverage < coverage_threshold:
        reasons.append(f"Coverage {coverage:.2%} below threshold {coverage_threshold:.2%}")

    # Gate 2: Minimum cohort size
    unique_users = len(set(s.user_id for s in ok_snapshots))
    if unique_users < min_cohort_n:
        reasons.append(f"Cohort size {unique_users} below minimum {min_cohort_n}")

    # Gate 3: Stability (median absolute percentile change week-to-week)
    # Group by user and compute week-to-week changes
    from collections import defaultdict
    from datetime import timedelta

    user_snapshots: dict[UUID, list[RankPredictionSnapshot]] = defaultdict(list)
    for s in ok_snapshots:
        if s.predicted_percentile is not None:
            user_snapshots[s.user_id].append(s)

    abs_changes: list[float] = []
    for user_id, user_snaps in user_snapshots.items():
        # Sort by computed_at
        user_snaps_sorted = sorted(user_snaps, key=lambda x: x.computed_at)
        for i in range(1, len(user_snaps_sorted)):
            prev = user_snaps_sorted[i - 1]
            curr = user_snaps_sorted[i]

            # Check if within ~7 days
            delta_days = (curr.computed_at - prev.computed_at).total_seconds() / 86400
            if 5 <= delta_days <= 9:  # Roughly weekly
                if prev.predicted_percentile is not None and curr.predicted_percentile is not None:
                    abs_change = abs(curr.predicted_percentile - prev.predicted_percentile)
                    abs_changes.append(abs_change)

    if abs_changes:
        import statistics

        median_abs_change = statistics.median(abs_changes)
        if median_abs_change > stability_threshold:
            reasons.append(
                f"Stability median abs change {median_abs_change:.4f} above threshold {stability_threshold:.4f}"
            )
    else:
        reasons.append("Insufficient data for stability check")

    eligible = len(reasons) == 0
    return eligible, reasons
