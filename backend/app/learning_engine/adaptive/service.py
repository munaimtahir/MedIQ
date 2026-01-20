"""Adaptive Selection v0 service wrapper with run logging."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.adaptive.v0 import select_questions_v0
from app.learning_engine.constants import AlgoKey
from app.learning_engine.registry import resolve_active
from app.learning_engine.runs import log_run_failure, log_run_start, log_run_success

logger = logging.getLogger(__name__)


async def adaptive_select_v0(
    db: AsyncSession,
    user_id: UUID,
    *,
    year: int,
    block_ids: list[UUID],
    theme_ids: list[UUID] | None,
    count: int,
    mode: str,
    trigger: str = "api",
) -> dict[str, Any]:
    """
    Select questions using adaptive algorithm with run logging.
    
    Args:
        db: Database session
        user_id: User ID
        year: Academic year
        block_ids: Block IDs
        theme_ids: Optional theme filter
        count: Number of questions
        mode: Session mode
        trigger: Run trigger source
    
    Returns:
        Dictionary with question_ids and metadata
    """
    try:
        # Resolve active version and params
        version, params_obj = await resolve_active(db, AlgoKey.ADAPTIVE.value)
        if not version or not params_obj:
            logger.warning("No active adaptive algorithm version or params found")
            return {
                "question_ids": [],
                "count": 0,
                "error": "no_active_algo",
            }
        
        params = params_obj.params_json
        
        # Start run logging
        run = await log_run_start(
            db,
            algo_version_id=version.id,
            params_id=params_obj.id,
            user_id=user_id,
            session_id=None,
            trigger=trigger,
            input_summary={
                "user_id": str(user_id),
                "year": year,
                "block_ids": [str(bid) for bid in block_ids],
                "theme_ids": [str(tid) for tid in theme_ids] if theme_ids else None,
                "count": count,
                "mode": mode,
            },
        )
        
        # Call selection algorithm
        question_ids = await select_questions_v0(
            db,
            user_id,
            year=year,
            block_ids=block_ids,
            theme_ids=theme_ids,
            count=count,
            mode=mode,
            params=params,
        )
        
        # Compute distribution for output summary
        # (Would need to query questions again to get theme/difficulty distribution)
        # For now, keep it simple
        
        # Log success
        await log_run_success(
            db,
            run_id=run.id,
            output_summary={
                "count": len(question_ids),
                "requested": count,
            },
        )
        
        return {
            "question_ids": question_ids,
            "count": len(question_ids),
            "run_id": str(run.id),
        }
    
    except Exception as e:
        logger.error(f"Adaptive selection failed for user {user_id}: {e}")
        
        # Log failure if run was started
        if 'run' in locals():
            await log_run_failure(db, run_id=run.id, error_message=str(e))
        
        return {
            "question_ids": [],
            "count": 0,
            "error": str(e),
        }
