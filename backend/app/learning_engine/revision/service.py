"""Revision Scheduler v0 service."""

import logging
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.learning_engine.constants import AlgoKey
from app.learning_engine.registry import resolve_active
from app.learning_engine.runs import log_run_failure, log_run_start, log_run_success
from app.models.learning_mastery import UserThemeMastery
from app.models.learning_revision import RevisionQueue

logger = logging.getLogger(__name__)


def get_mastery_band(mastery_score: float, mastery_bands: list[dict]) -> str:
    """
    Determine mastery band for a score.

    Args:
        mastery_score: Mastery score (0..1)
        mastery_bands: List of band definitions with name and max

    Returns:
        Band name (e.g., "weak", "medium", "strong", "mastered")
    """
    for band in mastery_bands:
        if mastery_score <= band["max"]:
            return band["name"]
    return mastery_bands[-1]["name"]  # Default to last band


def compute_spacing_days(
    band: str,
    last_attempt_at: datetime | None,
    spacing_days: dict[str, int],
    current_date: date,
) -> tuple[date, bool]:
    """
    Compute next due date based on mastery band and spacing rules.

    Args:
        band: Mastery band name
        last_attempt_at: Last attempt timestamp
        spacing_days: Spacing configuration per band
        current_date: Reference date

    Returns:
        Tuple of (due_date, is_due_now)
    """
    spacing = spacing_days.get(band, 1)

    if last_attempt_at is None:
        # Never attempted, due now
        return current_date, True

    last_attempt_date = last_attempt_at.date()
    next_due = last_attempt_date + timedelta(days=spacing)

    is_due_now = next_due <= current_date

    return next_due, is_due_now


def compute_priority_score(
    mastery_score: float,
    attempts_total: int,
    last_attempt_at: datetime | None,
    current_date: date,
    priority_weights: dict[str, float],
    min_attempts: int,
) -> float:
    """
    Compute priority score for ordering revision items.

    Higher score = higher priority.

    Args:
        mastery_score: Mastery score (0..1)
        attempts_total: Total attempts
        last_attempt_at: Last attempt timestamp
        current_date: Reference date
        priority_weights: Weight configuration
        min_attempts: Minimum attempts threshold

    Returns:
        Priority score
    """
    mastery_inverse_weight = priority_weights.get("mastery_inverse", 70)
    recency_weight = priority_weights.get("recency", 2)
    low_data_bonus_weight = priority_weights.get("low_data_bonus", 10)

    # Component 1: Inverse mastery (weak themes = higher priority)
    mastery_component = (1.0 - mastery_score) * mastery_inverse_weight

    # Component 2: Recency (older = higher priority)
    recency_component = 0.0
    if last_attempt_at:
        days_since = (current_date - last_attempt_at.date()).days
        recency_component = min(days_since, 90) * recency_weight  # Cap at 90 days

    # Component 3: Low data bonus
    low_data_component = 0.0
    if attempts_total < min_attempts:
        low_data_component = low_data_bonus_weight

    priority = mastery_component + recency_component + low_data_component

    return round(priority, 2)


def get_recommended_count(
    band: str,
    attempts_total: int,
    question_counts: dict[str, list[int]],
    min_attempts: int,
) -> int:
    """
    Get recommended question count based on band and attempts.

    Args:
        band: Mastery band name
        attempts_total: Total attempts
        question_counts: Count ranges per band
        min_attempts: Minimum attempts threshold

    Returns:
        Recommended question count
    """
    count_range = question_counts.get(band, [10, 10])

    # If low attempts, use lower bound
    if attempts_total < min_attempts:
        return count_range[0]

    # Otherwise use upper bound
    return count_range[1]


async def compute_revision_queue_v0(
    db: AsyncSession,
    user_id: UUID,
    params: dict[str, Any],
    current_date: date,
    year: int | None = None,
    block_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Compute revision queue items for a user.

    Args:
        db: Database session
        user_id: User ID
        params: Algorithm parameters
        current_date: Reference date
        year: Optional year filter
        block_id: Optional block filter

    Returns:
        List of revision queue item dictionaries
    """
    horizon_days = params.get("horizon_days", 7)
    min_attempts = params.get("min_attempts", 5)
    mastery_bands = params.get("mastery_bands", [])
    spacing_days = params.get("spacing_days", {})
    question_counts = params.get("question_counts", {})
    priority_weights = params.get("priority_weights", {})

    # Get all mastery records for user
    stmt = select(UserThemeMastery).where(UserThemeMastery.user_id == user_id)

    if year is not None:
        stmt = stmt.where(UserThemeMastery.year == year)
    if block_id is not None:
        stmt = stmt.where(UserThemeMastery.block_id == block_id)

    result = await db.execute(stmt)
    mastery_records = result.scalars().all()

    if not mastery_records:
        return []

    revision_items = []
    max_date = current_date + timedelta(days=horizon_days)

    for mastery in mastery_records:
        # Determine mastery band
        band = get_mastery_band(mastery.mastery_score, mastery_bands)

        # Compute spacing and due date
        due_date, is_due_now = compute_spacing_days(
            band,
            mastery.last_attempt_at,
            spacing_days,
            current_date,
        )

        # Skip if beyond horizon
        if due_date > max_date:
            continue

        # Compute priority
        priority = compute_priority_score(
            mastery.mastery_score,
            mastery.attempts_total,
            mastery.last_attempt_at,
            current_date,
            priority_weights,
            min_attempts,
        )

        # Get recommended count
        recommended_count = get_recommended_count(
            band,
            mastery.attempts_total,
            question_counts,
            min_attempts,
        )

        # Build reason
        reason = {
            "band": band,
            "mastery_score": float(mastery.mastery_score),
            "attempts_total": mastery.attempts_total,
            "spacing_days": spacing_days.get(band, 1),
            "last_attempt_days_ago": (
                (current_date - mastery.last_attempt_at.date()).days
                if mastery.last_attempt_at
                else None
            ),
            "is_due_now": is_due_now,
            "priority_breakdown": {
                "mastery_inverse": round(
                    (1.0 - mastery.mastery_score) * priority_weights.get("mastery_inverse", 70), 2
                ),
                "recency": round(
                    min(
                        (
                            (current_date - mastery.last_attempt_at.date()).days
                            if mastery.last_attempt_at
                            else 0
                        ),
                        90,
                    )
                    * priority_weights.get("recency", 2),
                    2,
                ),
                "low_data_bonus": (
                    priority_weights.get("low_data_bonus", 10)
                    if mastery.attempts_total < min_attempts
                    else 0
                ),
            },
        }

        revision_items.append(
            {
                "user_id": user_id,
                "year": mastery.year,
                "block_id": mastery.block_id,
                "theme_id": mastery.theme_id,
                "due_date": due_date,
                "priority_score": priority,
                "recommended_count": recommended_count,
                "status": "DUE",
                "reason_json": reason,
            }
        )

    return revision_items


async def upsert_revision_queue(
    db: AsyncSession,
    items: list[dict[str, Any]],
    algo_version_id: UUID,
    params_id: UUID,
    run_id: UUID,
) -> int:
    """
    Upsert revision queue items with status protection.

    Args:
        db: Database session
        items: List of revision queue item dictionaries
        algo_version_id: Algorithm version ID
        params_id: Parameter set ID
        run_id: Run ID

    Returns:
        Number of items upserted
    """
    if not items:
        return 0

    # Add provenance fields
    for item in items:
        item["algo_version_id"] = algo_version_id
        item["params_id"] = params_id
        item["run_id"] = run_id
        item["generated_at"] = datetime.utcnow()

    # Upsert with status protection
    # Only update if status is DUE (don't override DONE/SNOOZED/SKIPPED)
    stmt = insert(RevisionQueue).values(items)

    # On conflict, update only if current status is DUE
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "theme_id", "due_date"],
        set_={
            "priority_score": stmt.excluded.priority_score,
            "recommended_count": stmt.excluded.recommended_count,
            "reason_json": stmt.excluded.reason_json,
            "algo_version_id": stmt.excluded.algo_version_id,
            "params_id": stmt.excluded.params_id,
            "run_id": stmt.excluded.run_id,
            "generated_at": stmt.excluded.generated_at,
        },
        where=RevisionQueue.status == "DUE",
    )

    await db.execute(stmt)
    await db.commit()

    return len(items)


async def generate_revision_queue_v0(
    db: AsyncSession,
    user_id: UUID,
    *,
    year: int | None = None,
    block_id: int | None = None,
    trigger: str = "manual",
) -> dict[str, Any]:
    """
    Generate revision queue for a user.

    Args:
        db: Database session
        user_id: User ID
        year: Optional year filter
        block_id: Optional block filter
        trigger: Run trigger source

    Returns:
        Summary dictionary with counts
    """
    # Resolve active version and params
    version, params_obj = await resolve_active(db, AlgoKey.REVISION.value)
    if not version or not params_obj:
        raise ValueError("No active revision algorithm version or params found")

    params = params_obj.params_json
    current_date = date.today()

    # Start run logging
    run = await log_run_start(
        db,
        algo_version_id=version.id,
        params_id=params_obj.id,
        user_id=user_id,
        trigger=trigger,
        input_summary={
            "user_id": str(user_id),
            "year": year,
            "block_id": block_id,
            "horizon_days": params.get("horizon_days", 7),
        },
    )

    try:
        # Compute revision queue
        items = await compute_revision_queue_v0(db, user_id, params, current_date, year, block_id)

        # Count due today
        due_today = sum(1 for item in items if item["due_date"] == current_date)

        # Upsert items
        num_upserted = await upsert_revision_queue(db, items, version.id, params_obj.id, run.id)

        # Log success
        await log_run_success(
            db,
            run_id=run.id,
            output_summary={
                "generated": len(items),
                "due_today": due_today,
                "user_id": str(user_id),
            },
        )

        return {
            "generated": len(items),
            "due_today": due_today,
            "run_id": str(run.id),
        }

    except Exception as e:
        logger.error(f"Failed to generate revision queue for user {user_id}: {e}")
        await log_run_failure(db, run_id=run.id, error_message=str(e))
        raise
