"""Learning gain proxy metrics (offline-safe)."""

import logging
from collections import defaultdict
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def time_to_mastery(
    mastery_trajectories: dict[tuple[str, str], list[tuple[float, float]]],  # (user_id, concept_id) -> [(timestamp, mastery_score), ...]
    mastery_threshold: float = 0.85,
) -> dict[str, Any]:
    """
    Compute time-to-mastery proxy.

    For each (user, concept): count attempts needed to cross threshold the first time.

    Args:
        mastery_trajectories: Dictionary mapping (user_id, concept_id) to list of (timestamp, mastery_score) tuples
        mastery_threshold: Mastery threshold (default: 0.85)

    Returns:
        Dictionary with percentiles aggregated by scope
    """
    attempts_to_mastery = []

    for (user_id, concept_id), trajectory in mastery_trajectories.items():
        # Sort by timestamp
        trajectory.sort(key=lambda x: x[0])

        # Find first time mastery crosses threshold
        for attempt_num, (timestamp, mastery) in enumerate(trajectory, start=1):
            if mastery >= mastery_threshold:
                attempts_to_mastery.append(attempt_num)
                break

    if not attempts_to_mastery:
        return {
            "p50": None,
            "p75": None,
            "p90": None,
            "mean": None,
            "count": 0,
        }

    attempts_array = np.array(attempts_to_mastery)

    return {
        "p50": float(np.percentile(attempts_array, 50)),
        "p75": float(np.percentile(attempts_array, 75)),
        "p90": float(np.percentile(attempts_array, 90)),
        "mean": float(np.mean(attempts_array)),
        "count": len(attempts_to_mastery),
    }


def mastery_delta_per_horizon(
    mastery_start: dict[str, float],  # user_id -> mastery_score
    mastery_end: dict[str, float],  # user_id -> mastery_score
    horizon_days: int,
) -> dict[str, Any]:
    """
    Compute mastery delta over evaluation window.

    Args:
        mastery_start: Mastery scores at start of window
        mastery_end: Mastery scores at end of window
        horizon_days: Time horizon in days

    Returns:
        Dictionary with delta statistics
    """
    deltas = []
    common_users = set(mastery_start.keys()) & set(mastery_end.keys())

    for user_id in common_users:
        delta = mastery_end[user_id] - mastery_start[user_id]
        deltas.append(delta)

    if not deltas:
        return {
            "mean_delta": None,
            "median_delta": None,
            "positive_rate": None,
            "count": 0,
        }

    deltas_array = np.array(deltas)

    return {
        "mean_delta": float(np.mean(deltas_array)),
        "median_delta": float(np.median(deltas_array)),
        "positive_rate": float(np.mean(deltas_array > 0)),
        "count": len(deltas),
        "horizon_days": horizon_days,
    }


def retention_proxy(
    revisit_events: list[dict[str, Any]],  # List of {time_since_last_seen, predicted_recall, actual_outcome}
) -> dict[str, Any]:
    """
    Compute retention proxy for items revisited after >=X days.

    Args:
        revisit_events: List of events with time_since_last_seen, predicted_recall, actual_outcome

    Returns:
        Dictionary with retention metrics by time bins
    """
    if not revisit_events:
        return {"bins": []}

    # Bin by time since last seen
    time_bins = [0, 7, 14, 30, 60, 90, 180, 365]  # days
    bin_stats = defaultdict(lambda: {"predicted": [], "actual": [], "count": 0})

    for event in revisit_events:
        days = event.get("time_since_last_seen", 0)
        predicted = event.get("predicted_recall")
        actual = event.get("actual_outcome")

        # Find bin
        bin_idx = 0
        for i, bin_max in enumerate(time_bins[1:], start=1):
            if days <= bin_max:
                bin_idx = i - 1
                break
        else:
            bin_idx = len(time_bins) - 2  # Last bin

        bin_key = f"{time_bins[bin_idx]}-{time_bins[bin_idx + 1]}"
        if predicted is not None:
            bin_stats[bin_key]["predicted"].append(predicted)
        if actual is not None:
            bin_stats[bin_key]["actual"].append(1 if actual else 0)
        bin_stats[bin_key]["count"] += 1

    # Compute statistics per bin
    bin_results = []
    for bin_key in sorted(bin_stats.keys()):
        stats = bin_stats[bin_key]
        bin_results.append(
            {
                "time_range": bin_key,
                "count": stats["count"],
                "mean_predicted": float(np.mean(stats["predicted"])) if stats["predicted"] else None,
                "mean_actual": float(np.mean(stats["actual"])) if stats["actual"] else None,
            }
        )

    return {"bins": bin_results}


def difficulty_shift_guardrail(
    served_questions: list[dict[str, Any]],  # List of {timestamp, difficulty, ...}
    time_windows: list[tuple[float, float]],  # List of (start_time, end_time) tuples
) -> dict[str, Any]:
    """
    Guardrail: ensure improvements aren't only due to easier questions.

    Args:
        served_questions: List of questions with difficulty and timestamp
        time_windows: List of time windows to compare

    Returns:
        Dictionary with difficulty distribution per window
    """
    window_stats = []

    for window_start, window_end in time_windows:
        window_questions = [
            q for q in served_questions if window_start <= q.get("timestamp", 0) <= window_end
        ]

        if not window_questions:
            continue

        difficulties = [q.get("difficulty") for q in window_questions if q.get("difficulty") is not None]

        if not difficulties:
            continue

        window_stats.append(
            {
                "window": f"{window_start}-{window_end}",
                "mean_difficulty": float(np.mean(difficulties)),
                "median_difficulty": float(np.median(difficulties)),
                "count": len(difficulties),
            }
        )

    return {"windows": window_stats}
