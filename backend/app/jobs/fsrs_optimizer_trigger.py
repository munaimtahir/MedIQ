"""FSRS optimizer trigger - checks eligibility and enqueues training."""

import hashlib
import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.registry import create_job_run
from app.learning_engine.config import (
    FSRS_MIN_LOGS_FOR_TRAINING,
    FSRS_OPTIMIZER_COOLDOWN_DAYS,
)
from app.models.srs import SRSUserParams

logger = logging.getLogger(__name__)


async def check_and_trigger_optimizer(
    db: AsyncSession,
    user_id: UUID,
) -> bool:
    """
    Check if user is eligible for FSRS optimization and trigger if so.

    Eligibility:
    - n_review_logs >= FSRS_MIN_LOGS_FOR_TRAINING (300)
    - Cooldown period has passed (weekly)
    - Not already in cooldown

    A/B Assignment:
    - 50% users baseline (BASELINE_GLOBAL)
    - 50% tuned (TUNED_ELIGIBLE)
    - Assignment is stable (seeded by user_id hash)

    Args:
        db: Database session
        user_id: User ID

    Returns:
        True if job was enqueued, False otherwise
    """
    # Get user params
    user_params = await db.get(SRSUserParams, user_id)
    if not user_params:
        return False

    # Check eligibility
    if user_params.n_review_logs < FSRS_MIN_LOGS_FOR_TRAINING.value:
        return False

    # Check cooldown
    now = datetime.utcnow()
    if user_params.training_cooldown_until and user_params.training_cooldown_until > now:
        return False

    # Assign A/B group if not already assigned
    if not user_params.assigned_group:
        # Stable assignment based on user_id hash
        user_hash = int(hashlib.md5(str(user_id).encode()).hexdigest()[:8], 16)
        assigned_group = "TUNED_ELIGIBLE" if (user_hash % 2 == 0) else "BASELINE_GLOBAL"
        user_params.assigned_group = assigned_group
        await db.commit()
        logger.info(f"Assigned user {user_id} to group: {assigned_group}")

    # Only trigger for TUNED_ELIGIBLE group
    if user_params.assigned_group != "TUNED_ELIGIBLE":
        return False

    # Enqueue training job (store user_id in stats_json for processing)
    from app.jobs.registry import create_job_run

    job_run = await create_job_run(
        db,
        job_key="fsrs_train_user",
        scheduled_for=now,
    )

    # Store user_id in stats_json for job processor
    job_run.stats_json = {"user_id": str(user_id)}
    await db.commit()

    # Update cooldown
    cooldown_days = FSRS_OPTIMIZER_COOLDOWN_DAYS.value
    user_params.training_cooldown_until = now + timedelta(days=cooldown_days)
    await db.commit()

    logger.info(f"Enqueued FSRS training job for user {user_id}: {job_run.id}")
    return True


async def process_optimizer_eligibility_batch(
    db: AsyncSession,
    user_ids: list[UUID] | None = None,
) -> dict[str, int]:
    """
    Process a batch of users for optimizer eligibility.

    Args:
        db: Database session
        user_ids: List of user IDs to check (if None, checks all users)

    Returns:
        Statistics dictionary
    """
    if user_ids is None:
        # Get all users with SRS params
        stmt = select(SRSUserParams.user_id)
        result = await db.execute(stmt)
        user_ids = [row[0] for row in result.all()]

    triggered = 0
    skipped = 0

    for user_id in user_ids:
        try:
            if await check_and_trigger_optimizer(db, user_id):
                triggered += 1
            else:
                skipped += 1
        except Exception as e:
            logger.error(f"Error checking optimizer eligibility for user {user_id}: {e}")
            skipped += 1

    return {
        "triggered": triggered,
        "skipped": skipped,
        "total": len(user_ids),
    }
