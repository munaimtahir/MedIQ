"""Algorithm run logging helpers."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.constants import RunStatus, RunTrigger
from app.models.learning import AlgoRun

logger = logging.getLogger(__name__)


async def log_run_start(
    db: AsyncSession,
    algo_version_id: UUID,
    params_id: UUID,
    user_id: UUID | None = None,
    session_id: UUID | None = None,
    trigger: str = RunTrigger.MANUAL,
    input_summary: dict[str, Any] | None = None,
) -> AlgoRun:
    """
    Log the start of an algorithm run.
    
    Args:
        db: Database session
        algo_version_id: Algorithm version ID
        params_id: Parameter set ID
        user_id: Optional user ID (if user-specific run)
        session_id: Optional session ID (if session-triggered run)
        trigger: Run trigger source
        input_summary: Optional input summary dictionary
    
    Returns:
        Created AlgoRun instance
    """
    run = AlgoRun(
        id=uuid4(),
        algo_version_id=algo_version_id,
        params_id=params_id,
        user_id=user_id,
        session_id=session_id,
        trigger=trigger,
        status=RunStatus.RUNNING,
        started_at=datetime.utcnow(),
        input_summary_json=input_summary or {},
        output_summary_json={},
    )
    
    db.add(run)
    await db.commit()
    await db.refresh(run)
    
    logger.info(
        f"Started algo run: {run.id} (version: {algo_version_id}, params: {params_id})"
    )
    
    return run


async def log_run_success(
    db: AsyncSession,
    run_id: UUID,
    output_summary: dict[str, Any] | None = None,
) -> None:
    """
    Mark an algorithm run as successful.
    
    Args:
        db: Database session
        run_id: Run ID to update
        output_summary: Optional output summary dictionary
    """
    run = await db.get(AlgoRun, run_id)
    if not run:
        logger.error(f"Run not found: {run_id}")
        return
    
    run.status = RunStatus.SUCCESS
    run.completed_at = datetime.utcnow()
    if output_summary:
        run.output_summary_json = output_summary
    
    await db.commit()
    
    logger.info(f"Completed algo run successfully: {run_id}")


async def log_run_failure(
    db: AsyncSession,
    run_id: UUID,
    error_message: str,
) -> None:
    """
    Mark an algorithm run as failed.
    
    Args:
        db: Database session
        run_id: Run ID to update
        error_message: Error description
    """
    run = await db.get(AlgoRun, run_id)
    if not run:
        logger.error(f"Run not found: {run_id}")
        return
    
    run.status = RunStatus.FAILED
    run.completed_at = datetime.utcnow()
    run.error_message = error_message
    
    await db.commit()
    
    logger.error(f"Algo run failed: {run_id} - {error_message}")
