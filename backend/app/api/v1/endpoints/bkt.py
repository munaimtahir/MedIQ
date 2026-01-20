"""BKT (Bayesian Knowledge Tracing) API endpoints."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.bkt import (
    BKTRecomputeRequest,
    BKTRecomputeResponse,
    BKTRecomputeSummary,
    BKTUpdateInput,
    BKTUpdateResult,
    BKTUserSkillStateResponse,
)
from app.learning_engine.bkt.service import (
    get_user_mastery_state,
    update_bkt_from_attempt,
)
from app.learning_engine.bkt.training import (
    build_training_dataset,
    fit_bkt_parameters,
    persist_fitted_params,
)
from app.learning_engine.registry import resolve_active
from app.learning_engine.constants import AlgoKey
from app.learning_engine.runs import log_run_start, log_run_success, log_run_failure

router = APIRouter()
logger = logging.getLogger(__name__)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.post("/recompute", response_model=BKTRecomputeResponse)
async def recompute_bkt_params(
    request: BKTRecomputeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Recompute BKT parameters from historical data (Admin only).

    Fits BKT parameters using EM algorithm on historical attempt data.
    Optionally activates the newly fitted parameters.

    **Requires**: Admin role
    """
    # Resolve active BKT algorithm version
    algo_version, algo_params_obj = await resolve_active(db, AlgoKey.BKT)
    if not algo_version or not algo_params_obj:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="BKT algorithm not configured"
        )

    # Start run logging
    run = await log_run_start(
        db,
        algo_version_id=algo_version.id,
        params_id=algo_params_obj.id,
        user_id=None,  # Global recompute
        session_id=None,
        trigger="manual",
        input_summary={
            "from_date": request.from_date.isoformat() if request.from_date else None,
            "to_date": request.to_date.isoformat() if request.to_date else None,
            "min_attempts": request.min_attempts,
            "concept_count": len(request.concept_ids) if request.concept_ids else "all",
            "activate": request.activate_new_params,
        },
    )

    try:
        summary = BKTRecomputeSummary(
            concepts_processed=0,
            params_fitted=0,
            new_algo_version_id=algo_version.id,
            run_metrics={},
            errors={},
        )

        # Get concept IDs to process
        concept_ids = request.concept_ids or []

        if not concept_ids:
            # TODO: Query all concept IDs from concepts table
            # For now, return error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="concept_ids must be provided (all-concepts not yet implemented)",
            )

        # Process each concept
        for concept_id in concept_ids:
            summary.concepts_processed += 1

            try:
                # Build training dataset
                dataset = await build_training_dataset(
                    db,
                    concept_id=concept_id,
                    from_date=request.from_date,
                    to_date=request.to_date,
                    min_attempts_per_user=1,
                )

                # Check if sufficient data
                if not dataset.is_sufficient(min_attempts=request.min_attempts):
                    summary.errors[concept_id] = (
                        f"Insufficient data: {dataset.total_attempts} attempts"
                    )
                    continue

                # Fit parameters
                params, metrics, is_valid, message = await fit_bkt_parameters(
                    dataset,
                    constraints=None,  # Use defaults
                    use_cross_validation=False,
                )

                if not is_valid:
                    summary.errors[concept_id] = f"Fitting failed: {message}"
                    continue

                # Persist parameters
                await persist_fitted_params(
                    db,
                    concept_id=concept_id,
                    params=params,
                    metrics=metrics,
                    algo_version_id=algo_version.id,
                    from_date=request.from_date,
                    to_date=request.to_date,
                    constraints_applied={},
                    activate=request.activate_new_params,
                )

                summary.params_fitted += 1

            except Exception as e:
                logger.error(f"Error fitting concept {concept_id}: {e}", exc_info=True)
                summary.errors[concept_id] = str(e)

        # Commit all changes
        await db.commit()

        # Log success
        await log_run_success(
            db,
            run_id=run.id,
            output_summary={
                "concepts_processed": summary.concepts_processed,
                "params_fitted": summary.params_fitted,
                "errors_count": len(summary.errors),
            },
        )
        await db.commit()

        return BKTRecomputeResponse(
            ok=True,
            run_id=run.id,
            algo={
                "key": algo_version.algo_key.value,
                "version": algo_version.version,
            },
            params_id=algo_params_obj.id,
            summary=summary,
        )

    except Exception as e:
        logger.error(f"BKT recompute failed: {e}", exc_info=True)

        # Log failure
        await log_run_failure(db, run_id=run.id, error_message=str(e))
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BKT recompute failed: {str(e)}",
        )


@router.post("/update", response_model=BKTUpdateResult)
async def update_bkt_mastery(
    request: BKTUpdateInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update BKT mastery for a single attempt.

    This endpoint is typically called after a student answers a question.
    It updates the user's mastery probability for the concept using the BKT model.

    **Student scope**: Can only update own mastery (user_id must match current user or be None)
    **Admin scope**: Can update any user's mastery
    """
    # Determine target user
    target_user_id = request.user_id or current_user.id

    # Enforce student scope
    if current_user.role != "ADMIN" and target_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update mastery for other users"
        )

    # Use current time if not provided
    current_time = request.current_time or datetime.now()

    try:
        result = await update_bkt_from_attempt(
            db,
            user_id=target_user_id,
            question_id=request.question_id,
            concept_id=request.concept_id,
            correct=request.correct,
            current_time=current_time,
            snapshot_mastery=request.snapshot_mastery,
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"BKT update failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"BKT update failed: {str(e)}"
        )


@router.get("/mastery", response_model=list[BKTUserSkillStateResponse])
async def get_bkt_mastery(
    user_id: Optional[UUID] = None,
    concept_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get BKT mastery state for a user.

    **Student scope**: Can only query own mastery (user_id must match current user or be None)
    **Admin scope**: Can query any user's mastery

    Query params:
    - user_id: User ID (defaults to current user)
    - concept_id: Optional concept filter
    """
    # Determine target user
    target_user_id = user_id or current_user.id

    # Enforce student scope
    if current_user.role != "ADMIN" and target_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot query mastery for other users"
        )

    try:
        states = await get_user_mastery_state(db, target_user_id, concept_id)
        return states

    except Exception as e:
        logger.error(f"Failed to get BKT mastery: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get mastery: {str(e)}",
        )
