"""Warehouse incremental export job (runs nightly if enabled)."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.lock import acquire_job_lock, release_job_lock
from app.jobs.registry import create_job_run, update_job_run_status
from app.warehouse.exporter import _get_warehouse_mode, run_incremental_exports

logger = logging.getLogger(__name__)


async def run_warehouse_incremental_export(
    db: AsyncSession,
    scheduled_for: datetime | None = None,
) -> dict[str, Any]:
    """
    Run incremental warehouse exports for all datasets (nightly job).

    Only runs if warehouse_mode != disabled and warehouse_freeze == false.
    """
    job_key = "warehouse_incremental_export"

    # Acquire lock
    lock_acquired = await acquire_job_lock(db, job_key, lock_duration_minutes=120)
    if not lock_acquired:
        logger.warning(f"Job {job_key} is already running, skipping")
        return {"status": "skipped", "reason": "already_running"}

    # Create job run
    job_run = await create_job_run(db, job_key, scheduled_for)

    try:
        await update_job_run_status(db, job_run.id, "RUNNING")

        # Check warehouse mode and freeze (need sync session for exporter)
        from sqlalchemy.orm import Session
        from app.db.session import SessionLocal

        # Get sync session for warehouse mode check and export
        sync_db: Session = SessionLocal()
        try:
            warehouse_mode, warehouse_freeze = _get_warehouse_mode(sync_db)

        if warehouse_mode == "disabled":
            await update_job_run_status(
                db,
                job_run.id,
                "SUCCEEDED",
                stats={"status": "skipped", "reason": "warehouse_disabled"},
            )
            logger.info(f"Job {job_key} skipped: warehouse mode is disabled")
            return {"status": "skipped", "reason": "warehouse_disabled"}

        if warehouse_freeze:
            await update_job_run_status(
                db,
                job_run.id,
                "SUCCEEDED",
                stats={"status": "skipped", "reason": "warehouse_frozen"},
            )
            logger.info(f"Job {job_key} skipped: warehouse is frozen")
            return {"status": "skipped", "reason": "warehouse_frozen"}

            # Run incremental exports
            run_ids = run_incremental_exports(sync_db, None, "Nightly incremental export job")

            await update_job_run_status(
                db,
                job_run.id,
                "SUCCEEDED",
                stats={
                    "run_ids": [str(rid) for rid in run_ids],
                    "warehouse_mode": warehouse_mode,
                },
            )

            logger.info(f"Job {job_key} completed: {len(run_ids)} export runs started")
            return {"status": "succeeded", "run_ids": [str(rid) for rid in run_ids]}
        finally:
            sync_db.close()

    except Exception as e:
        logger.error(f"Job {job_key} failed: {e}", exc_info=True)
        await update_job_run_status(db, job_run.id, "FAILED", error=str(e))
        return {"status": "failed", "error": str(e)}
    finally:
        await release_job_lock(db, job_key)
