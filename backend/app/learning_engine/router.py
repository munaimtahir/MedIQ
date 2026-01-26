"""Algorithm router - routes requests to v0 or v1 based on runtime config.

This module provides the routing layer that selects which algorithm version
to use based on the runtime configuration, ensuring seamless fallback.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.runtime import (
    MODULE_ADAPTIVE,
    MODULE_DIFFICULTY,
    MODULE_IRT,
    MODULE_MASTERY,
    MODULE_MISTAKES,
    MODULE_REVISION,
    AlgoRuntimeProfile,
    get_algo_runtime_config,
    get_algo_version,
    get_session_algo_config,
    is_irt_active_allowed,
    is_safe_mode_freeze_updates,
)

logger = logging.getLogger(__name__)


async def _ensure_user_bridged(
    db: AsyncSession,
    user_id: UUID,
    target_profile: AlgoRuntimeProfile,
    policy_version: str = "ALGO_BRIDGE_SPEC_v1",
) -> None:
    """
    Ensure user state is bridged for the target profile (lazy bridging).

    Checks if bridge is needed and triggers it if missing.
    This is called on first request after a profile switch.
    """
    from app.models.algo_runtime import AlgoStateBridge
    from sqlalchemy import select

    # Check if bridge already exists for this profile transition
    # We need to determine the "from" profile (opposite of target)
    from_profile = (
        AlgoRuntimeProfile.V0_FALLBACK
        if target_profile == AlgoRuntimeProfile.V1_PRIMARY
        else AlgoRuntimeProfile.V1_PRIMARY
    )

    stmt = select(AlgoStateBridge).where(
        AlgoStateBridge.user_id == user_id,
        AlgoStateBridge.from_profile == from_profile,
        AlgoStateBridge.to_profile == target_profile,
        AlgoStateBridge.policy_version == policy_version,
        AlgoStateBridge.status == "done",
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Already bridged
        return

    # Trigger lazy bridge using bridge_runner
    logger.info(
        f"Triggering lazy bridge for user {user_id}: {from_profile.value} → {target_profile.value}"
    )
    try:
        from app.learning_engine.bridge.bridge_runner import ensure_user_bridged

        await ensure_user_bridged(user_id, from_profile, target_profile, policy_version, db)
    except Exception as e:
        logger.warning(f"Lazy bridge failed for user {user_id}: {e}. Continuing with request.")
        # Don't fail the request if bridge fails - it will be retried on next request


async def compute_mastery(
    db: AsyncSession,
    user_id: UUID,
    theme_id: int,
    session_profile: str | None = None,
    session_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Compute mastery for a user/theme, routing to v0 or v1.

    Args:
        db: Database session
        user_id: User ID
        theme_id: Theme ID
        session_profile: Session profile snapshot (if any)
        session_overrides: Session overrides snapshot (if any)

    Returns:
        Mastery computation result
    """
    # Get algorithm version for this session/request
    algo_config = await get_session_algo_config(db, session_profile, session_overrides)
    version = algo_config.get(MODULE_MASTERY, "v1")

    # Check safe mode
    if await is_safe_mode_freeze_updates(db):
        logger.info("Safe mode: freeze_updates enabled, returning cached mastery")
        # Return cached mastery from canonical state
        from app.models.algo_runtime import UserMasteryState
        from sqlalchemy import select

        stmt = select(UserMasteryState).where(
            UserMasteryState.user_id == user_id,
            UserMasteryState.theme_id == theme_id,
        )
        result = await db.execute(stmt)
        state = result.scalar_one_or_none()
        if state:
            return {
                "mastery_score": float(state.mastery_score),
                "model": state.mastery_model,
                "frozen": True,
            }
        return {"mastery_score": 0.0, "model": "v0", "frozen": True}

    # Route to appropriate version
    if version == "v0":
        from app.learning_engine.mastery.service import compute_mastery_v0

        return await compute_mastery_v0(db, user_id, theme_id)
    else:
        from app.learning_engine.bkt.service import compute_mastery_v1

        return await compute_mastery_v1(db, user_id, theme_id)


async def plan_revision(
    db: AsyncSession,
    user_id: UUID,
    session_profile: str | None = None,
    session_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Plan revision schedule, routing to v0 or v1.

    Args:
        db: Database session
        user_id: User ID
        session_profile: Session profile snapshot (if any)
        session_overrides: Session overrides snapshot (if any)

    Returns:
        Revision plan result
    """
    algo_config = await get_session_algo_config(db, session_profile, session_overrides)
    version = algo_config.get(MODULE_REVISION, "v1")

    if await is_safe_mode_freeze_updates(db):
        logger.info("Safe mode: freeze_updates enabled, returning cached revision plan")
        # Return cached revision queue
        from app.models.learning_revision import RevisionQueue
        from sqlalchemy import select
        from datetime import date

        stmt = (
            select(RevisionQueue)
            .where(RevisionQueue.user_id == user_id, RevisionQueue.status == "DUE")
            .order_by(RevisionQueue.priority_score.desc())
            .limit(50)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()
        return {
            "items": [
                {
                    "theme_id": item.theme_id,
                    "due_date": item.due_date.isoformat(),
                    "priority": float(item.priority_score),
                }
                for item in items
            ],
            "frozen": True,
        }

    if version == "v0":
        from app.learning_engine.revision.service import plan_revision_v0

        return await plan_revision_v0(db, user_id)
    else:
        from app.learning_engine.srs.service import plan_revision_v1

        return await plan_revision_v1(db, user_id)


async def adaptive_next(
    db: AsyncSession,
    user_id: UUID,
    context: dict[str, Any],
    session_profile: str | None = None,
    session_overrides: dict[str, Any] | None = None,
) -> list[UUID]:
    """
    Select next questions adaptively, routing to v0 or v1.

    Args:
        db: Database session
        user_id: User ID
        context: Selection context (year, blocks, count, mode, etc.)
        session_profile: Session profile snapshot (if any)
        session_overrides: Session overrides snapshot (if any)

    Returns:
        List of question IDs
    """
    algo_config = await get_session_algo_config(db, session_profile, session_overrides)
    version = algo_config.get(MODULE_ADAPTIVE, "v1")

    if version == "v0":
        from app.learning_engine.adaptive.v0 import select_questions_v0

        return await select_questions_v0(
            db,
            user_id,
            year=context["year"],
            block_ids=context["block_ids"],
            theme_ids=context.get("theme_ids"),
            count=context["count"],
            mode=context["mode"],
            params=context.get("params", {}),
        )
    else:
        from app.learning_engine.adaptive.service import adaptive_select_v0

        result = await adaptive_select_v0(
            db,
            user_id,
            year=context["year"],
            block_ids=context["block_ids"],
            theme_ids=context.get("theme_ids"),
            count=context["count"],
            mode=context["mode"],
        )
        return result


async def maybe_get_irt_estimates_for_session(
    session_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Get IRT estimates for a session (future-proof contract).

    This function MUST return None unless IRT is active-allowed.
    It respects session snapshot to ensure continuity.

    Args:
        session_id: Session ID
        user_id: User ID
        db: Database session
        snapshot: Session snapshot (algo_profile_at_start, algo_overrides_at_start)

    Returns:
        IRT estimates dict or None if IRT is not active
    """
    # Extract snapshot info
    session_profile = snapshot.get("algo_profile_at_start") if snapshot else None
    session_overrides = snapshot.get("algo_overrides_at_start") if snapshot else None

    # Get runtime config (respecting snapshot)
    runtime_cfg = await get_algo_runtime_config(db)

    # Check if IRT is active-allowed (respecting snapshot overrides)
    if session_overrides and MODULE_IRT in session_overrides:
        irt_override = session_overrides[MODULE_IRT]
        if irt_override == "v0":
            return None  # Explicitly disabled in session
    elif MODULE_IRT in runtime_cfg.overrides:
        irt_override = runtime_cfg.overrides[MODULE_IRT]
        if irt_override == "v0":
            return None  # Explicitly disabled globally

    # Check if IRT is active-allowed
    if not await is_irt_active_allowed(db, runtime_cfg):
        return None  # IRT not active

    # TODO: When IRT is actually used in sessions, implement:
    # - Load IRT item params for questions in session
    # - Compute ability estimates
    # - Return structured estimates

    # For now, return None (IRT is shadow-only)
    logger.debug(f"IRT estimates requested for session {session_id}, but IRT is shadow-only")
    return None.get("question_ids", [])


async def classify_mistakes(
    db: AsyncSession,
    attempt_id: UUID,
    context: dict[str, Any],
    session_profile: str | None = None,
    session_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Classify mistakes, routing to v0 or v1.

    Args:
        db: Database session
        attempt_id: Attempt ID
        context: Classification context
        session_profile: Session profile snapshot (if any)
        session_overrides: Session overrides snapshot (if any)

    Returns:
        Mistake classification result
    """
    algo_config = await get_session_algo_config(db, session_profile, session_overrides)
    version = algo_config.get(MODULE_MISTAKES, "v1")

    if version == "v0":
        from app.learning_engine.mistakes.v0 import classify_mistake_v0

        return await classify_mistake_v0(db, attempt_id, context)
    else:
        from app.learning_engine.mistakes_v1.service import classify_mistake_v1

        return await classify_mistake_v1(db, attempt_id, context)


# ============================================================================
# High-level wrapper functions for API endpoints (match service signatures)
# ============================================================================


async def recompute_mastery_for_user(
    db: AsyncSession,
    user_id: UUID,
    theme_ids: list[int] | None = None,
    dry_run: bool = False,
    session_profile: str | None = None,
    session_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Recompute mastery for a user, routing to v0 or v1.

    Wrapper that matches service signature for API endpoints.
    """
    # Get current runtime config (for lazy bridging)
    runtime_config = await get_algo_runtime_config(db)
    target_profile = runtime_config.active_profile

    # Ensure user is bridged if needed (lazy bridging)
    if not session_profile:  # Only bridge for non-session requests
        await _ensure_user_bridged(db, user_id, target_profile)

    algo_config = await get_session_algo_config(db, session_profile, session_overrides)
    version = algo_config.get(MODULE_MASTERY, "v1")

    if version == "v0":
        from app.learning_engine.mastery.service import recompute_mastery_v0_for_user

        return await recompute_mastery_v0_for_user(db, user_id, theme_ids, dry_run)
    else:
        # v1 BKT mastery - for now, fallback to v0 until v1 service is implemented
        # TODO: Implement recompute_mastery_v1_for_user in bkt.service
        logger.warning(f"BKT v1 mastery recompute not yet implemented, falling back to v0")
        from app.learning_engine.mastery.service import recompute_mastery_v0_for_user

        return await recompute_mastery_v0_for_user(db, user_id, theme_ids, dry_run)


async def generate_revision_queue_for_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    year: int | None = None,
    block_id: int | None = None,
    trigger: str = "api",
    session_profile: str | None = None,
    session_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate revision queue for a user, routing to v0 or v1.

    Wrapper that matches service signature for API endpoints.
    """
    # Get current runtime config (for lazy bridging)
    runtime_config = await get_algo_runtime_config(db)
    target_profile = runtime_config.active_profile

    # Ensure user is bridged if needed (lazy bridging)
    if not session_profile:  # Only bridge for non-session requests
        await _ensure_user_bridged(db, user_id, target_profile)

    algo_config = await get_session_algo_config(db, session_profile, session_overrides)
    version = algo_config.get(MODULE_REVISION, "v1")

    if version == "v0":
        from app.learning_engine.revision.service import generate_revision_queue_v0

        return await generate_revision_queue_v0(db, user_id, year=year, block_id=block_id, trigger=trigger)
    else:
        # v1 FSRS revision - for now, fallback to v0 until v1 service is implemented
        # TODO: Implement generate_revision_queue_v1 in srs.service
        logger.warning(f"FSRS v1 revision queue generation not yet implemented, falling back to v0")
        from app.learning_engine.revision.service import generate_revision_queue_v0

        return await generate_revision_queue_v0(db, user_id, year=year, block_id=block_id, trigger=trigger)


async def classify_mistakes_for_session(
    db: AsyncSession,
    session_id: UUID,
    trigger: str = "api",
    session_profile: str | None = None,
    session_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Classify mistakes for a session, routing to v0 or v1.

    Wrapper that matches service signature for API endpoints.
    """
    algo_config = await get_session_algo_config(db, session_profile, session_overrides)
    version = algo_config.get(MODULE_MISTAKES, "v1")

    if version == "v0":
        from app.learning_engine.mistakes.service import classify_mistakes_v0_for_session

        return await classify_mistakes_v0_for_session(db, session_id, trigger)
    else:
        # v1 ML mistakes - check if service exists
        try:
            from app.learning_engine.mistakes_v1.service import classify_mistakes_v1_for_session

            return await classify_mistakes_v1_for_session(db, session_id, trigger)
        except ImportError:
            # Fallback to v0 if v1 not available
            logger.warning(f"Mistakes v1 service not available, falling back to v0")
            from app.learning_engine.mistakes.service import classify_mistakes_v0_for_session

            return await classify_mistakes_v0_for_session(db, session_id, trigger)
