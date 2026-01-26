"""SRS (Spaced Repetition System) API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.learning_engine.srs.service import (
    get_due_concepts,
    get_user_stats,
)
from app.models.user import User
from app.schemas.srs import (
    SRSConceptStateResponse,
    SRSQueueItemResponse,
    SRSQueueResponse,
    SRSUserStatsResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/queue", response_model=SRSQueueResponse)
async def get_srs_queue(
    scope: str = Query("today", regex="^(today|week)$"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get SRS queue - concepts due for review.

    Query params:
    - scope: "today" (due now) or "week" (due in next 7 days)
    - limit: Max concepts to return (default 100)

    Returns concepts ordered by due_at (most overdue first).
    Priority score is computed from retrievability (lower = higher priority).
    """
    try:
        due_concepts = await get_due_concepts(
            db,
            user_id=current_user.id,
            scope=scope,
            limit=limit,
        )

        # Convert to response format
        items = [
            SRSQueueItemResponse(
                concept_id=c["concept_id"],
                due_at=c["due_at"],
                stability=c["stability"],
                difficulty=c["difficulty"],
                retrievability=c["retrievability"],
                priority_score=c["priority_score"],
                is_overdue=c["is_overdue"],
                days_overdue=c["days_overdue"],
                bucket=c["bucket"],
            )
            for c in due_concepts
        ]

        return SRSQueueResponse(
            scope=scope,
            total_due=len(items),
            items=items,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to get SRS queue: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SRS queue: {str(e)}",
        ) from e


@router.get("/stats", response_model=SRSUserStatsResponse)
async def get_srs_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get user's SRS statistics.

    Returns summary of concepts tracked, due counts, review counts, and
    personalization status.
    """
    try:
        stats = await get_user_stats(db, current_user.id)

        return SRSUserStatsResponse(
            total_concepts=stats["total_concepts"],
            due_today=stats["due_today"],
            due_this_week=stats["due_this_week"],
            total_reviews=stats["total_reviews"],
            has_personalized_weights=stats["has_personalized_weights"],
            last_trained_at=stats["last_trained_at"],
        )

    except Exception as e:
        logger.error(f"Failed to get SRS stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SRS stats: {str(e)}",
        ) from e


@router.get("/concepts/{concept_id}", response_model=SRSConceptStateResponse)
async def get_concept_state(
    concept_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get SRS state for a specific concept.

    Returns current stability, difficulty, due date, and retrievability.
    """
    from sqlalchemy import and_, select

    from app.models.srs import SRSConceptState

    try:
        result = await db.execute(
            select(SRSConceptState).where(
                and_(
                    SRSConceptState.user_id == current_user.id,
                    SRSConceptState.concept_id == concept_id,
                )
            )
        )
        state = result.scalar_one_or_none()

        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No SRS state found for concept {concept_id}",
            )

        return SRSConceptStateResponse.model_validate(state)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get concept state: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get concept state: {str(e)}",
        ) from e
