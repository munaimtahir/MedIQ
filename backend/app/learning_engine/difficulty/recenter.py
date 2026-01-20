"""
Drift control via recentering.

Prevents rating inflation/deflation by normalizing question ratings
while preserving relative differences (θ - b).
"""

import logging
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.constants import AlgoKey, RunStatus, RunTrigger
from app.learning_engine.registry import log_run_start, log_run_success, resolve_active
from app.learning_engine.runs import log_run_failure
from app.models.difficulty import DifficultyQuestionRating, DifficultyUserRating, RatingScope

logger = logging.getLogger(__name__)


async def recenter_question_ratings(
    db: AsyncSession,
    scope_type: RatingScope = RatingScope.GLOBAL,
    scope_id: Optional[UUID] = None,
) -> dict:
    """
    Recenter question ratings to mean=0 and adjust user ratings accordingly.

    Preserves relative differences (θ - b) by:
    1. Compute mean of all question ratings in scope
    2. Subtract mean from all question ratings
    3. Add mean to all user ratings

    Args:
        db: Database session
        scope_type: GLOBAL or THEME
        scope_id: None for GLOBAL, theme_id for THEME

    Returns:
        Summary dict with mean adjustment, counts
    """
    # Resolve active algo
    algo_version, algo_params = await resolve_active(db, AlgoKey.DIFFICULTY)
    if not algo_version or not algo_params:
        raise ValueError("Difficulty algorithm not configured")

    # Start algo run
    run_id = await log_run_start(
        db,
        algo_version_id=algo_version.id,
        params_id=algo_params.id,
        user_id=None,
        session_id=None,
        trigger=RunTrigger.MANUAL,
        input_summary_json={
            "scope_type": scope_type.value,
            "scope_id": str(scope_id) if scope_id else None,
        },
    )

    try:
        # Compute mean question rating in scope
        stmt = select(func.avg(DifficultyQuestionRating.rating)).where(
            DifficultyQuestionRating.scope_type == scope_type.value,
            DifficultyQuestionRating.scope_id == scope_id,
        )
        result = await db.execute(stmt)
        mean_rating = result.scalar()

        if mean_rating is None or abs(mean_rating) < 0.01:
            # Already centered or no data
            await log_run_success(
                db,
                run_id=run_id,
                output_summary_json={"mean_adjustment": 0.0, "already_centered": True},
            )
            return {
                "mean_adjustment": 0.0,
                "questions_updated": 0,
                "users_updated": 0,
                "already_centered": True,
            }

        # Count ratings
        count_stmt = select(func.count(DifficultyQuestionRating.id)).where(
            DifficultyQuestionRating.scope_type == scope_type.value,
            DifficultyQuestionRating.scope_id == scope_id,
        )
        result = await db.execute(count_stmt)
        n_questions = result.scalar()

        count_stmt = select(func.count(DifficultyUserRating.id)).where(
            DifficultyUserRating.scope_type == scope_type.value,
            DifficultyUserRating.scope_id == scope_id,
        )
        result = await db.execute(count_stmt)
        n_users = result.scalar()

        # Adjust question ratings: b_new = b - mean (center at 0)
        stmt = (
            update(DifficultyQuestionRating)
            .where(
                DifficultyQuestionRating.scope_type == scope_type.value,
                DifficultyQuestionRating.scope_id == scope_id,
            )
            .values(
                rating=DifficultyQuestionRating.rating - mean_rating,
                updated_at=datetime.now(UTC),
            )
        )
        await db.execute(stmt)

        # Adjust user ratings: θ_new = θ - mean (preserve θ - b differences)
        # Note: Both adjust in same direction to preserve differences exactly
        stmt = (
            update(DifficultyUserRating)
            .where(
                DifficultyUserRating.scope_type == scope_type.value,
                DifficultyUserRating.scope_id == scope_id,
            )
            .values(
                rating=DifficultyUserRating.rating - mean_rating,
                updated_at=datetime.now(UTC),
            )
        )
        await db.execute(stmt)

        await db.commit()

        # Log success
        await log_run_success(
            db,
            run_id=run_id,
            output_summary_json={
                "mean_adjustment": float(mean_rating),
                "questions_updated": n_questions,
                "users_updated": n_users,
            },
        )

        logger.info(
            f"Recentered {scope_type.value} ratings: "
            f"mean adjustment={mean_rating:.2f}, "
            f"{n_questions} questions, {n_users} users"
        )

        return {
            "mean_adjustment": float(mean_rating),
            "questions_updated": n_questions,
            "users_updated": n_users,
            "already_centered": False,
        }

    except Exception as e:
        await log_run_failure(
            db,
            run_id=run_id,
            error_message=str(e),
        )
        raise


async def check_drift_and_recenter_if_needed(
    db: AsyncSession,
    threshold: float = 50.0,
) -> dict:
    """
    Check if drift exceeds threshold and recenter if needed.

    Args:
        db: Database session
        threshold: Recenter if abs(mean) > threshold

    Returns:
        Summary dict
    """
    # Check global mean
    stmt = select(func.avg(DifficultyQuestionRating.rating)).where(
        DifficultyQuestionRating.scope_type == RatingScope.GLOBAL.value,
        DifficultyQuestionRating.scope_id.is_(None),
    )
    result = await db.execute(stmt)
    mean_rating = result.scalar()

    if mean_rating is None:
        return {"drift_detected": False, "mean": 0.0}

    if abs(mean_rating) > threshold:
        logger.warning(f"Drift detected: mean question rating = {mean_rating:.2f}")
        recenter_result = await recenter_question_ratings(db, RatingScope.GLOBAL, None)
        return {
            "drift_detected": True,
            "mean": float(mean_rating),
            "recentered": True,
            **recenter_result,
        }

    return {
        "drift_detected": False,
        "mean": float(mean_rating),
    }
