"""
Evaluation metrics for difficulty calibration.

Computes calibration quality from update logs:
- Log loss
- Brier score
- Expected Calibration Error (ECE)
"""

import math
from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.difficulty import DifficultyUpdateLog, RatingScope


async def compute_logloss(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    theme_id: Optional[UUID] = None,
    days: int = 30,
) -> float:
    """
    Compute log loss (cross-entropy) from recent updates.

    Formula:
        LogLoss = -mean(y * log(p) + (1-y) * log(1-p))

    Where:
        y = actual outcome (0 or 1)
        p = predicted probability

    Args:
        db: Database session
        user_id: Filter by user (optional)
        theme_id: Filter by theme (optional)
        days: Lookback window in days

    Returns:
        Log loss value (lower is better, 0 = perfect, ~0.693 = random guessing)
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Build query
    stmt = select(
        DifficultyUpdateLog.score,
        DifficultyUpdateLog.p_pred,
    ).where(DifficultyUpdateLog.created_at >= cutoff)

    if user_id:
        stmt = stmt.where(DifficultyUpdateLog.user_id == user_id)
    if theme_id:
        stmt = stmt.where(DifficultyUpdateLog.theme_id == theme_id)

    result = await db.execute(stmt)
    logs = result.all()

    if not logs:
        return 0.0

    # Compute log loss
    epsilon = 1e-15  # Prevent log(0)
    total_loss = 0.0

    for score, p_pred in logs:
        y = 1.0 if score else 0.0
        p = max(epsilon, min(1.0 - epsilon, p_pred))

        loss = -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))
        total_loss += loss

    return total_loss / len(logs)


async def compute_brier_score(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    theme_id: Optional[UUID] = None,
    days: int = 30,
) -> float:
    """
    Compute Brier score from recent updates.

    Formula:
        Brier = mean((p - y)^2)

    Where:
        p = predicted probability
        y = actual outcome (0 or 1)

    Args:
        db: Database session
        user_id: Filter by user (optional)
        theme_id: Filter by theme (optional)
        days: Lookback window in days

    Returns:
        Brier score (lower is better, 0 = perfect, 0.25 = random guessing)
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Build query
    stmt = select(
        DifficultyUpdateLog.score,
        DifficultyUpdateLog.p_pred,
    ).where(DifficultyUpdateLog.created_at >= cutoff)

    if user_id:
        stmt = stmt.where(DifficultyUpdateLog.user_id == user_id)
    if theme_id:
        stmt = stmt.where(DifficultyUpdateLog.theme_id == theme_id)

    result = await db.execute(stmt)
    logs = result.all()

    if not logs:
        return 0.0

    # Compute Brier score
    total_error = 0.0

    for score, p_pred in logs:
        y = 1.0 if score else 0.0
        error = (p_pred - y) ** 2
        total_error += error

    return total_error / len(logs)


async def compute_calibration_curve(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    theme_id: Optional[UUID] = None,
    days: int = 30,
    n_bins: int = 10,
) -> dict:
    """
    Compute calibration curve (predicted vs observed accuracy by bin).

    Args:
        db: Database session
        user_id: Filter by user (optional)
        theme_id: Filter by theme (optional)
        days: Lookback window in days
        n_bins: Number of probability bins

    Returns:
        Dict with:
            - bins: List of (bin_start, bin_end, predicted_mean, observed_freq, count)
            - ece: Expected Calibration Error
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Build query
    stmt = select(
        DifficultyUpdateLog.score,
        DifficultyUpdateLog.p_pred,
    ).where(DifficultyUpdateLog.created_at >= cutoff)

    if user_id:
        stmt = stmt.where(DifficultyUpdateLog.user_id == user_id)
    if theme_id:
        stmt = stmt.where(DifficultyUpdateLog.theme_id == theme_id)

    result = await db.execute(stmt)
    logs = result.all()

    if not logs:
        return {"bins": [], "ece": 0.0}

    # Create bins
    bin_edges = [i / n_bins for i in range(n_bins + 1)]
    bins = [[] for _ in range(n_bins)]

    # Assign to bins
    for score, p_pred in logs:
        bin_idx = min(int(p_pred * n_bins), n_bins - 1)
        bins[bin_idx].append((score, p_pred))

    # Compute bin statistics
    bin_stats = []
    total_ece = 0.0
    total_count = len(logs)

    for i, bin_data in enumerate(bins):
        if not bin_data:
            continue

        bin_start = bin_edges[i]
        bin_end = bin_edges[i + 1]

        # Predicted mean
        predicted_mean = sum(p for _, p in bin_data) / len(bin_data)

        # Observed frequency
        observed_freq = sum(1 if s else 0 for s, _ in bin_data) / len(bin_data)

        # ECE contribution
        bin_weight = len(bin_data) / total_count
        ece_contribution = bin_weight * abs(predicted_mean - observed_freq)
        total_ece += ece_contribution

        bin_stats.append(
            {
                "bin_start": bin_start,
                "bin_end": bin_end,
                "predicted_mean": predicted_mean,
                "observed_freq": observed_freq,
                "count": len(bin_data),
            }
        )

    return {
        "bins": bin_stats,
        "ece": total_ece,
    }


async def compute_all_metrics(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    theme_id: Optional[UUID] = None,
    days: int = 30,
) -> dict:
    """
    Compute all calibration metrics.

    Args:
        db: Database session
        user_id: Filter by user (optional)
        theme_id: Filter by theme (optional)
        days: Lookback window in days

    Returns:
        Dict with logloss, brier, calibration curve, and ECE
    """
    logloss = await compute_logloss(db, user_id, theme_id, days)
    brier = await compute_brier_score(db, user_id, theme_id, days)
    calibration = await compute_calibration_curve(db, user_id, theme_id, days)

    return {
        "logloss": logloss,
        "brier": brier,
        "ece": calibration["ece"],
        "calibration_curve": calibration["bins"],
        "window_days": days,
    }
