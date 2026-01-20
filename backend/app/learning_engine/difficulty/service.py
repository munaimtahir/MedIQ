"""
Difficulty calibration service layer.

Handles database operations and orchestrates rating updates.
Supports both global and theme-scoped ratings with uncertainty tracking.
"""

import logging
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.config import (
    ELO_GUESS_FLOOR,
    ELO_K_BASE_QUESTION,
    ELO_K_BASE_USER,
    ELO_K_MAX,
    ELO_K_MIN,
    ELO_MIN_ATTEMPTS_THEME_QUESTION,
    ELO_MIN_ATTEMPTS_THEME_USER,
    ELO_RATING_INIT,
    ELO_SCALE,
    ELO_THEME_UPDATE_WEIGHT,
    ELO_UNC_AGE_INCREASE_PER_DAY,
    ELO_UNC_DECAY_PER_ATTEMPT,
    ELO_UNC_FLOOR,
    ELO_UNC_INIT_QUESTION,
    ELO_UNC_INIT_USER,
)
from app.learning_engine.constants import AlgoKey
from app.learning_engine.difficulty.core import (
    apply_update,
    compute_delta,
    compute_dynamic_k,
    p_correct,
    update_uncertainty,
    validate_rating_finite,
)
from app.learning_engine.registry import resolve_active
from app.models.difficulty import (
    DifficultyQuestionRating,
    DifficultyUpdateLog,
    DifficultyUserRating,
    RatingScope,
)

logger = logging.getLogger(__name__)


async def get_or_create_user_rating(
    db: AsyncSession,
    user_id: UUID,
    scope_type: RatingScope,
    scope_id: Optional[UUID],
    params: dict,
) -> DifficultyUserRating:
    """
    Get or create user rating for given scope.

    Args:
        db: Database session
        user_id: User ID
        scope_type: GLOBAL or THEME
        scope_id: None for GLOBAL, theme_id for THEME
        params: Algorithm parameters

    Returns:
        User rating object
    """
    # Try to fetch existing
    stmt = select(DifficultyUserRating).where(
        DifficultyUserRating.user_id == user_id,
        DifficultyUserRating.scope_type == scope_type.value,
        DifficultyUserRating.scope_id == scope_id,
    )
    result = await db.execute(stmt)
    rating_obj = result.scalar_one_or_none()

    if rating_obj:
        return rating_obj

    # Create new
    rating_obj = DifficultyUserRating(
        user_id=user_id,
        scope_type=scope_type.value,
        scope_id=scope_id,
        rating=params.get("rating_init", ELO_RATING_INIT.value),
        uncertainty=params.get("unc_init_user", ELO_UNC_INIT_USER.value),
        n_attempts=0,
        last_seen_at=None,
    )
    db.add(rating_obj)
    await db.flush()

    return rating_obj


async def get_or_create_question_rating(
    db: AsyncSession,
    question_id: UUID,
    scope_type: RatingScope,
    scope_id: Optional[UUID],
    params: dict,
) -> DifficultyQuestionRating:
    """
    Get or create question rating for given scope.

    Args:
        db: Database session
        question_id: Question ID
        scope_type: GLOBAL or THEME
        scope_id: None for GLOBAL, theme_id for THEME
        params: Algorithm parameters

    Returns:
        Question rating object
    """
    # Try to fetch existing
    stmt = select(DifficultyQuestionRating).where(
        DifficultyQuestionRating.question_id == question_id,
        DifficultyQuestionRating.scope_type == scope_type.value,
        DifficultyQuestionRating.scope_id == scope_id,
    )
    result = await db.execute(stmt)
    rating_obj = result.scalar_one_or_none()

    if rating_obj:
        return rating_obj

    # Create new
    rating_obj = DifficultyQuestionRating(
        question_id=question_id,
        scope_type=scope_type.value,
        scope_id=scope_id,
        rating=params.get("rating_init", ELO_RATING_INIT.value),
        uncertainty=params.get("unc_init_question", ELO_UNC_INIT_QUESTION.value),
        n_attempts=0,
        last_seen_at=None,
    )
    db.add(rating_obj)
    await db.flush()

    return rating_obj


async def update_difficulty_from_attempt(
    db: AsyncSession,
    *,
    user_id: UUID,
    question_id: UUID,
    theme_id: Optional[UUID],
    score: bool,
    attempt_id: Optional[UUID] = None,
    occurred_at: Optional[datetime] = None,
) -> dict:
    """
    Update difficulty ratings from a single attempt.

    Performs:
    1. Load/create GLOBAL user and question ratings
    2. Compute predicted probability
    3. Update GLOBAL ratings with dynamic K
    4. Conditionally update THEME ratings (if enough data)
    5. Log update with pre/post snapshots

    Args:
        db: Database session
        user_id: User ID
        question_id: Question ID
        theme_id: Theme ID (optional, for theme-scoped updates)
        score: True if correct, False if incorrect
        attempt_id: Unique attempt ID (for idempotency)
        occurred_at: Timestamp of attempt (defaults to now)

    Returns:
        Summary dict with p_pred, updated ratings, scope info
    """
    if occurred_at is None:
        occurred_at = datetime.now(UTC)

    # Resolve active algorithm version and params
    algo_version, algo_params = await resolve_active(db, AlgoKey.DIFFICULTY)
    if not algo_version or not algo_params:
        raise ValueError("Difficulty algorithm not configured (no active version/params)")

    params = algo_params.params_json or {}

    # Extract params with fallbacks
    guess_floor = params.get("guess_floor", ELO_GUESS_FLOOR.value)
    scale = params.get("scale", ELO_SCALE.value)
    k_base_user = params.get("k_base_user", ELO_K_BASE_USER.value)
    k_base_question = params.get("k_base_question", ELO_K_BASE_QUESTION.value)
    k_min = params.get("k_min", ELO_K_MIN.value)
    k_max = params.get("k_max", ELO_K_MAX.value)
    unc_floor = params.get("unc_floor", ELO_UNC_FLOOR.value)
    unc_decay = params.get("unc_decay_per_attempt", ELO_UNC_DECAY_PER_ATTEMPT.value)
    unc_age_rate = params.get("unc_age_increase_per_day", ELO_UNC_AGE_INCREASE_PER_DAY.value)
    min_attempts_theme_user = params.get(
        "min_attempts_theme_user", ELO_MIN_ATTEMPTS_THEME_USER.value
    )
    min_attempts_theme_question = params.get(
        "min_attempts_theme_question", ELO_MIN_ATTEMPTS_THEME_QUESTION.value
    )
    theme_weight = params.get("theme_update_weight", ELO_THEME_UPDATE_WEIGHT.value)

    # Check for duplicate attempt_id (idempotency)
    if attempt_id:
        stmt = select(DifficultyUpdateLog).where(DifficultyUpdateLog.attempt_id == attempt_id)
        result = await db.execute(stmt)
        existing_log = result.scalar_one_or_none()
        if existing_log:
            logger.info(f"Skipping duplicate attempt {attempt_id}")
            return {
                "duplicate": True,
                "p_pred": existing_log.p_pred,
                "scope_updated": existing_log.scope_used,
            }

    # === STEP 1: Load GLOBAL ratings ===
    user_global = await get_or_create_user_rating(db, user_id, RatingScope.GLOBAL, None, params)
    question_global = await get_or_create_question_rating(
        db, question_id, RatingScope.GLOBAL, None, params
    )

    # Capture pre-update state
    user_rating_pre = user_global.rating
    user_unc_pre = user_global.uncertainty
    q_rating_pre = question_global.rating
    q_unc_pre = question_global.uncertainty

    # === STEP 2: Compute predicted probability ===
    p_pred = p_correct(user_global.rating, question_global.rating, guess_floor, scale)

    # === STEP 3: Compute error ===
    delta = compute_delta(score, p_pred)

    # === STEP 4: Update uncertainties ===
    user_global.uncertainty = update_uncertainty(
        user_global.uncertainty,
        user_global.n_attempts,
        user_global.last_seen_at,
        occurred_at,
        unc_floor,
        unc_decay,
        unc_age_rate,
    )
    question_global.uncertainty = update_uncertainty(
        question_global.uncertainty,
        question_global.n_attempts,
        question_global.last_seen_at,
        occurred_at,
        unc_floor,
        unc_decay,
        unc_age_rate,
    )

    # === STEP 5: Compute dynamic K ===
    k_u = compute_dynamic_k(k_base_user, user_global.uncertainty, k_min, k_max)
    k_q = compute_dynamic_k(k_base_question, question_global.uncertainty, k_min, k_max)

    # === STEP 6: Apply GLOBAL rating updates ===
    theta_new, b_new = apply_update(
        user_global.rating,
        question_global.rating,
        k_u,
        k_q,
        delta,
    )

    # Validate finite
    validate_rating_finite(theta_new, "user_rating_global")
    validate_rating_finite(b_new, "question_rating_global")

    user_global.rating = theta_new
    question_global.rating = b_new
    user_global.n_attempts += 1
    question_global.n_attempts += 1
    user_global.last_seen_at = occurred_at
    question_global.last_seen_at = occurred_at
    user_global.updated_at = occurred_at
    question_global.updated_at = occurred_at

    # Mark for update
    db.add(user_global)
    db.add(question_global)

    # Capture post-update state
    user_rating_post = user_global.rating
    user_unc_post = user_global.uncertainty
    q_rating_post = question_global.rating
    q_unc_post = question_global.uncertainty

    scope_updated = "GLOBAL"

    # === STEP 7: Conditionally update THEME ratings ===
    if theme_id:
        # Check if we have enough data for theme-specific ratings
        user_has_theme_data = user_global.n_attempts >= min_attempts_theme_user
        question_has_theme_data = question_global.n_attempts >= min_attempts_theme_question

        if user_has_theme_data and question_has_theme_data:
            # Load/create theme ratings
            user_theme = await get_or_create_user_rating(
                db, user_id, RatingScope.THEME, theme_id, params
            )
            question_theme = await get_or_create_question_rating(
                db, question_id, RatingScope.THEME, theme_id, params
            )

            # Update theme uncertainties
            user_theme.uncertainty = update_uncertainty(
                user_theme.uncertainty,
                user_theme.n_attempts,
                user_theme.last_seen_at,
                occurred_at,
                unc_floor,
                unc_decay,
                unc_age_rate,
            )
            question_theme.uncertainty = update_uncertainty(
                question_theme.uncertainty,
                question_theme.n_attempts,
                question_theme.last_seen_at,
                occurred_at,
                unc_floor,
                unc_decay,
                unc_age_rate,
            )

            # Compute theme-specific K (weighted by theme_weight)
            k_u_theme = (
                compute_dynamic_k(k_base_user, user_theme.uncertainty, k_min, k_max) * theme_weight
            )
            k_q_theme = (
                compute_dynamic_k(k_base_question, question_theme.uncertainty, k_min, k_max)
                * theme_weight
            )

            # Apply theme updates
            theta_theme_new, b_theme_new = apply_update(
                user_theme.rating,
                question_theme.rating,
                k_u_theme,
                k_q_theme,
                delta,
            )

            # Validate finite
            validate_rating_finite(theta_theme_new, "user_rating_theme")
            validate_rating_finite(b_theme_new, "question_rating_theme")

            user_theme.rating = theta_theme_new
            question_theme.rating = b_theme_new
            user_theme.n_attempts += 1
            question_theme.n_attempts += 1
            user_theme.last_seen_at = occurred_at
            question_theme.last_seen_at = occurred_at
            user_theme.updated_at = occurred_at
            question_theme.updated_at = occurred_at

            db.add(user_theme)
            db.add(question_theme)

            scope_updated = "BOTH"

    # === STEP 8: Log update ===
    update_log = DifficultyUpdateLog(
        attempt_id=attempt_id,
        user_id=user_id,
        question_id=question_id,
        theme_id=theme_id,
        scope_used=scope_updated,
        score=score,
        p_pred=p_pred,
        user_rating_pre=user_rating_pre,
        user_rating_post=user_rating_post,
        user_unc_pre=user_unc_pre,
        user_unc_post=user_unc_post,
        q_rating_pre=q_rating_pre,
        q_rating_post=q_rating_post,
        q_unc_pre=q_unc_pre,
        q_unc_post=q_unc_post,
        k_u_used=k_u,
        k_q_used=k_q,
        guess_floor_used=guess_floor,
        scale_used=scale,
        algo_version_id=algo_version.id,
        params_id=algo_params.id,
        run_id=None,  # For per-attempt updates, run_id is None
        created_at=occurred_at,
    )
    db.add(update_log)

    # Commit all changes
    await db.commit()

    # Return summary
    return {
        "p_pred": p_pred,
        "user_rating_global": user_rating_post,
        "question_rating_global": q_rating_post,
        "scope_updated": scope_updated,
        "k_u_used": k_u,
        "k_q_used": k_q,
        "algo_version": algo_version.version,
        "params_id": str(algo_params.id),
    }


async def update_difficulty_for_session(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
    attempts: list[dict],
) -> dict:
    """
    Update difficulty ratings for all attempts in a session.

    Args:
        db: Database session
        session_id: Test session ID
        user_id: User ID
        attempts: List of attempt dicts with keys:
            - attempt_id (optional)
            - question_id
            - theme_id (optional)
            - score (bool)
            - occurred_at (optional)

    Returns:
        Summary dict with counts and average p_pred
    """
    updates_count = 0
    p_pred_sum = 0.0
    errors = []

    for attempt in attempts:
        try:
            result = await update_difficulty_from_attempt(
                db,
                user_id=user_id,
                question_id=attempt["question_id"],
                theme_id=attempt.get("theme_id"),
                score=attempt["score"],
                attempt_id=attempt.get("attempt_id"),
                occurred_at=attempt.get("occurred_at"),
            )

            if not result.get("duplicate"):
                updates_count += 1
                p_pred_sum += result["p_pred"]
        except Exception as e:
            logger.warning(
                f"Failed to update difficulty for attempt {attempt.get('attempt_id')}: {e}"
            )
            errors.append(str(e))

    avg_p_pred = p_pred_sum / updates_count if updates_count > 0 else 0.0

    return {
        "session_id": str(session_id),
        "updates_count": updates_count,
        "avg_p_pred": avg_p_pred,
        "errors": errors,
    }
