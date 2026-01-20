"""
Difficulty calibration API endpoints.

Provides:
- Internal update from attempts
- Question difficulty lookup
- User ability lookup
- Admin health check
- Admin recenter operation
- Admin metrics
"""

import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.learning_engine.difficulty.metrics import compute_all_metrics
from app.learning_engine.difficulty.recenter import recenter_question_ratings
from app.learning_engine.difficulty.service import update_difficulty_for_session
from app.models.difficulty import (
    DifficultyQuestionRating,
    DifficultyUpdateLog,
    DifficultyUserRating,
    RatingScope,
)
from app.models.user import User, UserRole
from app.schemas.difficulty import (
    HealthMetrics,
    MetricsResponse,
    QuestionDifficultyResponse,
    RatingInfo,
    RecenterResponse,
    UpdateDifficultyRequest,
    UpdateDifficultyResponse,
    UserAbilityResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def require_admin(current_user: User):
    """Check if user is admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.post("/update", response_model=UpdateDifficultyResponse)
async def update_difficulty(
    request: UpdateDifficultyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Update difficulty ratings from attempts.

    This is an internal endpoint called by the backend.
    Students can only update their own attempts.
    """
    # Validate session ownership if session_id provided
    if request.session_id:
        from app.models.session import TestSession

        stmt = select(TestSession).where(TestSession.id == request.session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Not authorized to update this session")

    # Convert attempts to dict format
    attempts = [
        {
            "attempt_id": a.attempt_id,
            "question_id": a.question_id,
            "theme_id": a.theme_id,
            "score": a.score,
            "occurred_at": a.occurred_at,
        }
        for a in request.attempts
    ]

    # Update difficulty
    result = await update_difficulty_for_session(
        db,
        session_id=request.session_id,
        user_id=current_user.id,
        attempts=attempts,
    )

    # Get algo version from first successful update
    algo_version = "v1"  # Default

    return UpdateDifficultyResponse(
        ok=True,
        algo_version=algo_version,
        updates_count=result["updates_count"],
        avg_p_pred=result["avg_p_pred"],
        errors=result["errors"],
    )


@router.get("/question/{question_id}", response_model=QuestionDifficultyResponse)
async def get_question_difficulty(
    question_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get difficulty rating for a question.

    Returns global rating and theme-specific ratings if available.
    """
    # Get global rating
    stmt = select(DifficultyQuestionRating).where(
        DifficultyQuestionRating.question_id == question_id,
        DifficultyQuestionRating.scope_type == RatingScope.GLOBAL.value,
        DifficultyQuestionRating.scope_id.is_(None),
    )
    result = await db.execute(stmt)
    global_rating = result.scalar_one_or_none()

    if not global_rating:
        raise HTTPException(status_code=404, detail="Question rating not found")

    # Get theme ratings
    stmt = select(DifficultyQuestionRating).where(
        DifficultyQuestionRating.question_id == question_id,
        DifficultyQuestionRating.scope_type == RatingScope.THEME.value,
    )
    result = await db.execute(stmt)
    theme_ratings = result.scalars().all()

    theme_ratings_dict = {}
    for tr in theme_ratings:
        theme_ratings_dict[str(tr.scope_id)] = RatingInfo(
            rating=tr.rating,
            uncertainty=tr.uncertainty,
            n_attempts=tr.n_attempts,
            last_seen_at=tr.last_seen_at,
        )

    return QuestionDifficultyResponse(
        question_id=question_id,
        global_rating=RatingInfo(
            rating=global_rating.rating,
            uncertainty=global_rating.uncertainty,
            n_attempts=global_rating.n_attempts,
            last_seen_at=global_rating.last_seen_at,
        ),
        theme_ratings=theme_ratings_dict,
    )


@router.get("/me", response_model=UserAbilityResponse)
async def get_my_ability(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get ability rating for current user.

    Returns global rating and theme-specific ratings if available.
    """
    # Get global rating
    stmt = select(DifficultyUserRating).where(
        DifficultyUserRating.user_id == current_user.id,
        DifficultyUserRating.scope_type == RatingScope.GLOBAL.value,
        DifficultyUserRating.scope_id.is_(None),
    )
    result = await db.execute(stmt)
    global_rating = result.scalar_one_or_none()

    if not global_rating:
        # No rating yet - user hasn't attempted any questions
        return UserAbilityResponse(
            user_id=current_user.id,
            global_rating=RatingInfo(
                rating=0.0,
                uncertainty=350.0,
                n_attempts=0,
                last_seen_at=None,
            ),
            theme_ratings={},
        )

    # Get theme ratings
    stmt = select(DifficultyUserRating).where(
        DifficultyUserRating.user_id == current_user.id,
        DifficultyUserRating.scope_type == RatingScope.THEME.value,
    )
    result = await db.execute(stmt)
    theme_ratings = result.scalars().all()

    theme_ratings_dict = {}
    for tr in theme_ratings:
        theme_ratings_dict[str(tr.scope_id)] = RatingInfo(
            rating=tr.rating,
            uncertainty=tr.uncertainty,
            n_attempts=tr.n_attempts,
            last_seen_at=tr.last_seen_at,
        )

    return UserAbilityResponse(
        user_id=current_user.id,
        global_rating=RatingInfo(
            rating=global_rating.rating,
            uncertainty=global_rating.uncertainty,
            n_attempts=global_rating.n_attempts,
            last_seen_at=global_rating.last_seen_at,
        ),
        theme_ratings=theme_ratings_dict,
    )


@router.get("/admin/health", response_model=HealthMetrics)
async def get_health_metrics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get system health metrics (admin only).

    Returns calibration metrics and drift indicators.
    """
    require_admin(current_user)

    from datetime import UTC, datetime, timedelta

    # Count totals
    stmt = select(func.count(DifficultyUserRating.id)).where(
        DifficultyUserRating.scope_type == RatingScope.GLOBAL.value
    )
    result = await db.execute(stmt)
    total_users = result.scalar() or 0

    stmt = select(func.count(DifficultyQuestionRating.id)).where(
        DifficultyQuestionRating.scope_type == RatingScope.GLOBAL.value
    )
    result = await db.execute(stmt)
    total_questions = result.scalar() or 0

    stmt = select(func.count(DifficultyUpdateLog.id))
    result = await db.execute(stmt)
    total_updates = result.scalar() or 0

    # Recent updates (24h)
    cutoff_24h = datetime.now(UTC) - timedelta(hours=24)
    stmt = select(func.count(DifficultyUpdateLog.id)).where(
        DifficultyUpdateLog.created_at >= cutoff_24h
    )
    result = await db.execute(stmt)
    recent_updates_24h = result.scalar() or 0

    # Calibration metrics (30 days)
    metrics = await compute_all_metrics(db, days=30)

    # Mean question rating (drift indicator)
    stmt = select(func.avg(DifficultyQuestionRating.rating)).where(
        DifficultyQuestionRating.scope_type == RatingScope.GLOBAL.value,
        DifficultyQuestionRating.scope_id.is_(None),
    )
    result = await db.execute(stmt)
    mean_q_rating = result.scalar() or 0.0

    # Drift detected if abs(mean) > 50
    drift_detected = abs(mean_q_rating) > 50.0

    return HealthMetrics(
        total_users=total_users,
        total_questions=total_questions,
        total_updates=total_updates,
        recent_updates_24h=recent_updates_24h,
        logloss_30d=metrics["logloss"],
        brier_30d=metrics["brier"],
        ece_30d=metrics["ece"],
        mean_question_rating=float(mean_q_rating),
        drift_detected=drift_detected,
    )


@router.post("/admin/recenter", response_model=RecenterResponse)
async def recenter_ratings(
    scope_type: Annotated[str, Query()] = "GLOBAL",
    scope_id: Annotated[Optional[UUID], Query()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Recenter question ratings to prevent drift (admin only).

    Subtracts mean from question ratings and adds to user ratings,
    preserving relative differences (θ - b).
    """
    require_admin(current_user)

    # Validate scope_type
    try:
        scope_enum = RatingScope(scope_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scope_type (must be GLOBAL or THEME)")

    result = await recenter_question_ratings(db, scope_enum, scope_id)

    return RecenterResponse(
        ok=True,
        mean_adjustment=result["mean_adjustment"],
        questions_updated=result["questions_updated"],
        users_updated=result["users_updated"],
        already_centered=result.get("already_centered", False),
    )


@router.get("/admin/metrics", response_model=MetricsResponse)
async def get_detailed_metrics(
    days: Annotated[int, Query()] = 30,
    user_id: Annotated[Optional[UUID], Query()] = None,
    theme_id: Annotated[Optional[UUID], Query()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Get detailed calibration metrics (admin only).

    Returns logloss, Brier score, ECE, and calibration curve.
    """
    require_admin(current_user)

    metrics = await compute_all_metrics(db, user_id, theme_id, days)

    from app.schemas.difficulty import CalibrationBin

    return MetricsResponse(
        logloss=metrics["logloss"],
        brier=metrics["brier"],
        ece=metrics["ece"],
        calibration_curve=[CalibrationBin(**bin_data) for bin_data in metrics["calibration_curve"]],
        window_days=metrics["window_days"],
    )
