"""Stability metrics for learning algorithms."""

import logging
from typing import Any

import numpy as np
from scipy.stats import spearmanr

logger = logging.getLogger(__name__)


def parameter_drift(
    param_snapshots: list[dict[str, float]],
) -> dict[str, Any]:
    """
    Compute parameter drift across rolling windows.

    Args:
        param_snapshots: List of parameter dictionaries, one per time window

    Returns:
        Dictionary with drift metrics
    """
    if len(param_snapshots) < 2:
        return {"mean_absolute_drift": None, "max_drift": None, "drifts": []}

    # Compute drift between consecutive snapshots
    drifts = []
    param_names = set()
    for snapshot in param_snapshots:
        param_names.update(snapshot.keys())

    for i in range(len(param_snapshots) - 1):
        prev = param_snapshots[i]
        curr = param_snapshots[i + 1]
        window_drift = {}
        for param_name in param_names:
            prev_val = prev.get(param_name, 0.0)
            curr_val = curr.get(param_name, 0.0)
            window_drift[param_name] = abs(curr_val - prev_val)
        drifts.append(window_drift)

    # Aggregate across all parameters
    all_drifts = [d for window_drift in drifts for d in window_drift.values()]
    mean_absolute_drift = float(np.mean(all_drifts)) if all_drifts else None
    max_drift = float(np.max(all_drifts)) if all_drifts else None

    return {
        "mean_absolute_drift": mean_absolute_drift,
        "max_drift": max_drift,
        "drifts": drifts,
    }


def recommendation_stability(
    recommendations_by_day: dict[str, list[str]],  # day -> list of recommended items
    top_n: int = 10,
) -> dict[str, Any]:
    """
    Compute recommendation stability metrics.

    Args:
        recommendations_by_day: Dictionary mapping day identifier to list of recommended items
        top_n: Number of top items to consider

    Returns:
        Dictionary with stability metrics
    """
    if len(recommendations_by_day) < 2:
        return {
            "jaccard_overlap_mean": None,
            "volatility_rate": None,
            "overlaps": [],
        }

    days = sorted(recommendations_by_day.keys())
    overlaps = []
    top_1_changes = 0

    for i in range(len(days) - 1):
        day1 = days[i]
        day2 = days[i + 1]

        rec1 = set(recommendations_by_day[day1][:top_n])
        rec2 = set(recommendations_by_day[day2][:top_n])

        # Jaccard overlap
        intersection = len(rec1 & rec2)
        union = len(rec1 | rec2)
        jaccard = intersection / union if union > 0 else 0.0
        overlaps.append(jaccard)

        # Top-1 change
        if rec1 and rec2:
            top1_1 = list(rec1)[0] if rec1 else None
            top1_2 = list(rec2)[0] if rec2 else None
            if top1_1 != top1_2:
                top_1_changes += 1

    jaccard_mean = float(np.mean(overlaps)) if overlaps else None
    volatility_rate = top_1_changes / (len(days) - 1) if len(days) > 1 else None

    return {
        "jaccard_overlap_mean": jaccard_mean,
        "volatility_rate": volatility_rate,
        "overlaps": overlaps,
        "top_1_changes": top_1_changes,
        "total_days": len(days),
    }


def rank_stability(
    ranks_by_window: dict[str, dict[str, float]],  # window -> user_id -> score
) -> dict[str, Any]:
    """
    Compute rank stability (Spearman correlation across windows).

    Args:
        ranks_by_window: Dictionary mapping window identifier to user_id -> score mapping

    Returns:
        Dictionary with rank stability metrics
    """
    if len(ranks_by_window) < 2:
        return {"spearman_correlations": [], "mean_correlation": None}

    windows = sorted(ranks_by_window.keys())
    correlations = []

    for i in range(len(windows) - 1):
        window1 = windows[i]
        window2 = windows[i + 1]

        scores1 = ranks_by_window[window1]
        scores2 = ranks_by_window[window2]

        # Get common users
        common_users = set(scores1.keys()) & set(scores2.keys())
        if len(common_users) < 2:
            continue

        # Extract scores for common users
        scores1_list = [scores1[uid] for uid in common_users]
        scores2_list = [scores2[uid] for uid in common_users]

        # Compute Spearman correlation
        try:
            corr, p_value = spearmanr(scores1_list, scores2_list)
            correlations.append({"correlation": float(corr), "p_value": float(p_value), "n": len(common_users)})
        except Exception as e:
            logger.warning(f"Rank stability computation failed: {e}")

    mean_correlation = float(np.mean([c["correlation"] for c in correlations])) if correlations else None

    return {
        "spearman_correlations": correlations,
        "mean_correlation": mean_correlation,
    }
