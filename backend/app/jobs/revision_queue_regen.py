"""Revision queue regeneration job (runs at 2am)."""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.lock import acquire_job_lock, release_job_lock
from app.jobs.registry import create_job_run, update_job_run_status
from app.models.queues import QueueStatsDaily, RevisionQueueTheme, RevisionQueueUserSummary
from app.models.srs import SRSConceptState

logger = logging.getLogger(__name__)


async def regenerate_revision_queues(
    db: AsyncSession,
    scheduled_for: datetime | None = None,
) -> dict[str, Any]:
    """
    Regenerate revision queues for all users.

    This job:
    1. Queries FSRS due concepts (due_at <= end_of_today) and overdue
    2. Maps concepts → themes (using syllabus mapping)
    3. Computes theme_due_count per user
    4. Writes to revision_queue_theme and revision_queue_user_summary
    5. Writes daily snapshot to queue_stats_daily

    Args:
        db: Database session
        scheduled_for: Scheduled execution time

    Returns:
        Statistics dictionary
    """
    job_key = "revision_queue_regen"

    # Acquire lock
    lock_acquired = await acquire_job_lock(db, job_key, lock_duration_minutes=120)
    if not lock_acquired:
        logger.warning(f"Job {job_key} is already running, skipping")
        return {"status": "skipped", "reason": "already_running"}

    # Create job run
    job_run = await create_job_run(db, job_key, scheduled_for)

    try:
        await update_job_run_status(db, job_run.id, "RUNNING")

        today = date.today()
        end_of_today = datetime.combine(today, datetime.max.time())
        tomorrow = today + timedelta(days=1)
        end_of_tomorrow = datetime.combine(tomorrow, datetime.max.time())

        logger.info(f"Starting revision queue regeneration for {today}")

        # Get all users with FSRS concept states
        stmt = select(SRSConceptState.user_id).distinct()
        result = await db.execute(stmt)
        user_ids = [row[0] for row in result.all()]

        logger.info(f"Found {len(user_ids)} users with FSRS states")

        # Process users in batches
        batch_size = 200
        processed_users = 0
        total_due_today = 0
        total_overdue = 0
        total_due_tomorrow = 0

        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i : i + batch_size]
            await _process_user_batch(db, batch, today, end_of_today, end_of_tomorrow)

            processed_users += len(batch)
            logger.info(f"Processed {processed_users}/{len(user_ids)} users...")

        # Compute global stats
        stmt = select(
            func.sum(RevisionQueueUserSummary.due_today_total),
            func.sum(RevisionQueueUserSummary.overdue_total),
            func.sum(RevisionQueueUserSummary.due_tomorrow_total),
            func.count(RevisionQueueUserSummary.user_id),
        )
        result = await db.execute(stmt)
        row = result.first()
        if row:
            total_due_today = row[0] or 0
            total_overdue = row[1] or 0
            total_due_tomorrow = row[2] or 0
            users_with_due = row[3] or 0

        # Write daily snapshot
        await _write_daily_snapshot(db, today, total_due_today, total_overdue, total_due_tomorrow, users_with_due)

        stats = {
            "processed_users": processed_users,
            "due_today_total": total_due_today,
            "overdue_total": total_overdue,
            "due_tomorrow_total": total_due_tomorrow,
            "users_with_due": users_with_due,
        }

        await update_job_run_status(db, job_run.id, "SUCCEEDED", stats=stats)
        logger.info(f"Revision queue regeneration completed: {stats}")

        return {"status": "success", **stats}

    except Exception as e:
        logger.error(f"Revision queue regeneration failed: {e}", exc_info=True)
        await update_job_run_status(db, job_run.id, "FAILED", error=str(e))
        raise
    finally:
        await release_job_lock(db, job_key)


async def _process_user_batch(
    db: AsyncSession,
    user_ids: list[UUID],
    today: date,
    end_of_today: datetime,
    end_of_tomorrow: datetime,
) -> None:
    """Process a batch of users."""
    # Get FSRS concept states for these users
    stmt = select(SRSConceptState).where(
        SRSConceptState.user_id.in_(user_ids),
        SRSConceptState.due_at.isnot(None),
    )
    result = await db.execute(stmt)
    concept_states = result.scalars().all()

    # Group by user and theme (need to map concept_id → theme_id)
    user_theme_counts: dict[tuple[UUID, int], dict[str, int]] = defaultdict(
        lambda: {"due_today": 0, "overdue": 0, "due_tomorrow": 0}
    )
    user_next_due: dict[tuple[UUID, int], datetime] = {}

    # Import concept mapping helper
    from app.jobs.concept_mapping import get_theme_id_with_fallback

    for state in concept_states:
        if not state.due_at:
            continue

        # Map concept_id to theme_id with fallback
        # For now, use a simple hash-based mapping
        # TODO: Implement proper concept → theme mapping table
        theme_id = await get_theme_id_with_fallback(db, state.concept_id)

        key = (state.user_id, theme_id)

        if state.due_at <= end_of_today:
            if state.due_at.date() < today:
                user_theme_counts[key]["overdue"] += 1
            else:
                user_theme_counts[key]["due_today"] += 1
        elif state.due_at <= end_of_tomorrow:
            user_theme_counts[key]["due_tomorrow"] += 1

        # Track next due date
        if key not in user_next_due or state.due_at < user_next_due[key]:
            user_next_due[key] = state.due_at

    # Upsert revision_queue_theme
    from sqlalchemy.dialects.postgresql import insert

    theme_records = []
    for (user_id, theme_id), counts in user_theme_counts.items():
        # theme_id is already an integer
        theme_records.append(
            {
                "user_id": user_id,
                "theme_id": theme_id,
                "due_count_today": counts["due_today"],
                "overdue_count": counts["overdue"],
                "next_due_at": user_next_due.get((user_id, theme_id)),
                "updated_at": datetime.utcnow(),
            }
        )

    if theme_records:
        stmt = insert(RevisionQueueTheme).values(theme_records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "theme_id"],
            set_={
                "due_count_today": stmt.excluded.due_count_today,
                "overdue_count": stmt.excluded.overdue_count,
                "next_due_at": stmt.excluded.next_due_at,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await db.execute(stmt)

    # Upsert user summaries
    user_summaries: dict[UUID, dict[str, int]] = defaultdict(lambda: {"due_today": 0, "overdue": 0, "due_tomorrow": 0})

    for (user_id, _), counts in user_theme_counts.items():
        user_summaries[user_id]["due_today"] += counts["due_today"]
        user_summaries[user_id]["overdue"] += counts["overdue"]
        user_summaries[user_id]["due_tomorrow"] += counts["due_tomorrow"]

    summary_records = []
    for user_id, counts in user_summaries.items():
        summary_records.append(
            {
                "user_id": user_id,
                "due_today_total": counts["due_today"],
                "overdue_total": counts["overdue"],
                "due_tomorrow_total": counts["due_tomorrow"],
                "updated_at": datetime.utcnow(),
            }
        )

    if summary_records:
        stmt = insert(RevisionQueueUserSummary).values(summary_records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "due_today_total": stmt.excluded.due_today_total,
                "overdue_total": stmt.excluded.overdue_total,
                "due_tomorrow_total": stmt.excluded.due_tomorrow_total,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await db.execute(stmt)

    await db.commit()


async def _write_daily_snapshot(
    db: AsyncSession,
    snapshot_date: date,
    due_today_total: int,
    overdue_total: int,
    due_tomorrow_total: int,
    users_with_due: int,
) -> None:
    """Write daily queue statistics snapshot."""
    from sqlalchemy.dialects.postgresql import insert

    stmt = insert(QueueStatsDaily).values(
        {
            "date": snapshot_date,
            "due_today_total": due_today_total,
            "overdue_total": overdue_total,
            "due_tomorrow_total": due_tomorrow_total,
            "users_with_due": users_with_due,
            "created_at": datetime.utcnow(),
        }
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["date"],
        set_={
            "due_today_total": stmt.excluded.due_today_total,
            "overdue_total": stmt.excluded.overdue_total,
            "due_tomorrow_total": stmt.excluded.due_tomorrow_total,
            "users_with_due": stmt.excluded.users_with_due,
        },
    )
    await db.execute(stmt)
    await db.commit()
