"""Canonical state maintenance job.

Maintains canonical state tables (user_theme_stats, user_mastery_state, user_revision_state)
by syncing from source tables (attempt_events, user_theme_mastery, revision_queue).
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.algo_runtime import UserMasteryState, UserRevisionState, UserThemeStats
from app.models.attempt import AttemptEvent
from app.models.learning_mastery import UserThemeMastery
from app.models.learning_revision import RevisionQueue

logger = logging.getLogger(__name__)


async def maintain_user_theme_stats(
    db: AsyncSession,
    user_id: UUID | None = None,
    since_days: int = 7,
) -> dict[str, int]:
    """
    Maintain user_theme_stats from attempt_events.

    Args:
        db: Database session
        user_id: Optional user ID to process (if None, processes all active users)
        since_days: Only process attempts from last N days

    Returns:
        Dictionary with counts (processed, created, updated)
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)

    # Get distinct user_id, theme_id pairs from recent attempts
    stmt = (
        select(
            AttemptEvent.user_id,
            AttemptEvent.question_id,
            func.count(AttemptEvent.id).label("attempts"),
            func.sum(func.cast(AttemptEvent.payload_json["is_correct"], func.Integer)).label("correct"),
            func.max(AttemptEvent.event_ts).label("last_attempt_at"),
        )
        .where(AttemptEvent.event_ts >= cutoff)
        .group_by(AttemptEvent.user_id, AttemptEvent.question_id)
    )

    if user_id:
        stmt = stmt.where(AttemptEvent.user_id == user_id)

    result = await db.execute(stmt)
    rows = result.all()

    # Get theme_id for each question (simplified - would need proper join in production)
    # For now, we'll aggregate at question level and let the system derive theme stats
    # This is a placeholder - full implementation would join with questions table

    processed = 0
    created = 0
    updated = 0

    # TODO: Full implementation would:
    # 1. Join with questions table to get theme_id
    # 2. Aggregate by user_id, theme_id
    # 3. Upsert into user_theme_stats

    logger.info(f"Maintained theme stats: processed={processed}, created={created}, updated={updated}")

    return {"processed": processed, "created": created, "updated": updated}


async def sync_mastery_state_from_mastery_table(
    db: AsyncSession,
    user_id: UUID | None = None,
) -> dict[str, int]:
    """
    Sync user_mastery_state from user_theme_mastery.

    Copies mastery_score from user_theme_mastery to canonical user_mastery_state.

    Args:
        db: Database session
        user_id: Optional user ID to process (if None, processes all users)

    Returns:
        Dictionary with counts (synced, created, updated)
    """
    stmt = select(UserThemeMastery).order_by(UserThemeMastery.computed_at.desc())

    if user_id:
        stmt = stmt.where(UserThemeMastery.user_id == user_id)

    result = await db.execute(stmt)
    mastery_records = result.scalars().all()

    synced = 0
    created = 0
    updated = 0

    for record in mastery_records:
        # Check if canonical state exists
        stmt_canonical = select(UserMasteryState).where(
            UserMasteryState.user_id == record.user_id,
            UserMasteryState.theme_id == record.theme_id,
        )
        result_canonical = await db.execute(stmt_canonical)
        canonical = result_canonical.scalar_one_or_none()

        if not canonical:
            # Create new canonical state
            canonical = UserMasteryState(
                user_id=record.user_id,
                theme_id=record.theme_id,
                mastery_score=record.mastery_score,
                mastery_model=record.algo_version.version if record.algo_version else "v0",
                mastery_updated_at=record.computed_at,
            )
            db.add(canonical)
            created += 1
        else:
            # Update if newer
            if record.computed_at > canonical.mastery_updated_at:
                canonical.mastery_score = record.mastery_score
                canonical.mastery_model = record.algo_version.version if record.algo_version else "v0"
                canonical.mastery_updated_at = record.computed_at
                updated += 1

        synced += 1

    await db.commit()

    logger.info(f"Synced mastery state: synced={synced}, created={created}, updated={updated}")

    return {"synced": synced, "created": created, "updated": updated}


async def sync_revision_state_from_queue(
    db: AsyncSession,
    user_id: UUID | None = None,
) -> dict[str, int]:
    """
    Sync user_revision_state from revision_queue.

    Copies due_date from revision_queue to canonical user_revision_state.

    Args:
        db: Database session
        user_id: Optional user ID to process (if None, processes all users)

    Returns:
        Dictionary with counts (synced, created, updated)
    """
    stmt = select(RevisionQueue).where(RevisionQueue.status == "DUE").order_by(
        RevisionQueue.generated_at.desc()
    )

    if user_id:
        stmt = stmt.where(RevisionQueue.user_id == user_id)

    result = await db.execute(stmt)
    queue_items = result.scalars().all()

    synced = 0
    created = 0
    updated = 0

    for item in queue_items:
        # Check if canonical state exists
        stmt_canonical = select(UserRevisionState).where(
            UserRevisionState.user_id == item.user_id,
            UserRevisionState.theme_id == item.theme_id,
        )
        result_canonical = await db.execute(stmt_canonical)
        canonical = result_canonical.scalar_one_or_none()

        if not canonical:
            # Create new canonical state
            canonical = UserRevisionState(
                user_id=item.user_id,
                theme_id=item.theme_id,
                due_at=datetime.combine(item.due_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                updated_at=item.generated_at,
            )
            db.add(canonical)
            created += 1
        else:
            # Update if newer or if due_at is different
            item_due_at = datetime.combine(item.due_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            if item.generated_at > canonical.updated_at or canonical.due_at != item_due_at:
                canonical.due_at = item_due_at
                canonical.updated_at = item.generated_at
                updated += 1

        synced += 1

    await db.commit()

    logger.info(f"Synced revision state: synced={synced}, created={created}, updated={updated}")

    return {"synced": synced, "created": created, "updated": updated}


async def run_canonical_state_maintenance(
    db: AsyncSession,
    user_id: UUID | None = None,
    since_days: int = 7,
) -> dict[str, Any]:
    """
    Run all canonical state maintenance tasks.

    Args:
        db: Database session
        user_id: Optional user ID to process (if None, processes all users)
        since_days: Days to look back for attempt events

    Returns:
        Summary of all maintenance operations
    """
    logger.info(f"Starting canonical state maintenance (user_id={user_id}, since_days={since_days})")

    results = {}

    # 1. Maintain theme stats from attempt events
    try:
        results["theme_stats"] = await maintain_user_theme_stats(db, user_id, since_days)
    except Exception as e:
        logger.error(f"Theme stats maintenance failed: {e}")
        results["theme_stats"] = {"error": str(e)}

    # 2. Sync mastery state
    try:
        results["mastery_state"] = await sync_mastery_state_from_mastery_table(db, user_id)
    except Exception as e:
        logger.error(f"Mastery state sync failed: {e}")
        results["mastery_state"] = {"error": str(e)}

    # 3. Sync revision state
    try:
        results["revision_state"] = await sync_revision_state_from_queue(db, user_id)
    except Exception as e:
        logger.error(f"Revision state sync failed: {e}")
        results["revision_state"] = {"error": str(e)}

    logger.info(f"Canonical state maintenance completed: {results}")

    return results
