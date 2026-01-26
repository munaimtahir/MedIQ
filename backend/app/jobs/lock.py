"""Job locking mechanism to prevent concurrent execution."""

import logging
import socket
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jobs import JobLock

logger = logging.getLogger(__name__)


async def acquire_job_lock(
    db: AsyncSession,
    job_key: str,
    lock_duration_minutes: int = 60,
) -> bool:
    """
    Acquire a job lock (DB-based).

    Args:
        db: Database session
        job_key: Job key identifier
        lock_duration_minutes: Lock duration in minutes

    Returns:
        True if lock acquired, False if already locked
    """
    now = datetime.utcnow()
    lock_until = now + timedelta(minutes=lock_duration_minutes)
    locked_by = f"{socket.gethostname()}-{socket.gethostbyname(socket.gethostname())}"

    # Try to acquire lock
    stmt = (
        insert(JobLock)
        .values(
            job_key=job_key,
            locked_until=lock_until,
            locked_by=locked_by,
        )
        .on_conflict_do_update(
            index_elements=["job_key"],
            set_={
                "locked_until": lock_until,
                "locked_by": locked_by,
            },
            where=JobLock.locked_until < now,  # Only update if lock expired
        )
    )

    try:
        result = await db.execute(stmt)
        await db.commit()

        # Check if we actually got the lock
        check_stmt = select(JobLock).where(JobLock.job_key == job_key)
        check_result = await db.execute(check_stmt)
        lock = check_result.scalar_one_or_none()

        if lock and lock.locked_until > now and lock.locked_by == locked_by:
            logger.info(f"Acquired lock for job: {job_key}")
            return True
        else:
            logger.info(f"Failed to acquire lock for job: {job_key} (already locked)")
            return False

    except Exception as e:
        logger.error(f"Error acquiring lock: {e}")
        await db.rollback()
        return False


async def release_job_lock(
    db: AsyncSession,
    job_key: str,
) -> None:
    """
    Release a job lock.

    Args:
        db: Database session
        job_key: Job key identifier
    """
    stmt = select(JobLock).where(JobLock.job_key == job_key)
    result = await db.execute(stmt)
    lock = result.scalar_one_or_none()

    if lock:
        lock.locked_until = datetime.utcnow() - timedelta(minutes=1)  # Expire immediately
        await db.commit()
        logger.info(f"Released lock for job: {job_key}")
