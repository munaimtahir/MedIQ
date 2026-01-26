"""Job run registry for tracking job execution."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jobs import JobRun

logger = logging.getLogger(__name__)


async def create_job_run(
    db: AsyncSession,
    job_key: str,
    scheduled_for: datetime | None = None,
) -> JobRun:
    """
    Create a new job run.

    Args:
        db: Database session
        job_key: Job key identifier
        scheduled_for: Scheduled execution time

    Returns:
        Created JobRun
    """
    job_run = JobRun(
        id=uuid4(),
        job_key=job_key,
        scheduled_for=scheduled_for,
        status="QUEUED",
    )

    db.add(job_run)
    await db.commit()
    await db.refresh(job_run)

    logger.info(f"Created job run: {job_run.id} for job: {job_key}")
    return job_run


async def update_job_run_status(
    db: AsyncSession,
    run_id: UUID,
    status: str,
    stats: dict[str, Any] | None = None,
    error: str | None = None,
) -> JobRun:
    """
    Update job run status.

    Args:
        db: Database session
        run_id: Job run ID
        status: New status (QUEUED, RUNNING, SUCCEEDED, FAILED)
        stats: Optional statistics dictionary
        error: Error message if failed

    Returns:
        Updated JobRun
    """
    job_run = await db.get(JobRun, run_id)
    if not job_run:
        raise ValueError(f"Job run not found: {run_id}")

    job_run.status = status

    if status == "RUNNING":
        job_run.started_at = datetime.utcnow()
    elif status in ("SUCCEEDED", "FAILED"):
        job_run.finished_at = datetime.utcnow()

    if stats:
        job_run.stats_json = stats

    if error:
        job_run.error_text = error

    await db.commit()
    await db.refresh(job_run)
    return job_run
