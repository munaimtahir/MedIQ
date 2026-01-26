"""Bridge runner - idempotent per-user state conversion executor.

Implements ALGO_BRIDGE_SPEC_v1 with proper locking and idempotence.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.learning_engine.bridge.spec_v1 import (
    compute_v0_mastery_from_aggregates,
    init_bandit_beta_from_mastery,
    init_bkt_from_mastery,
    v0_to_v1_revision_bridge,
    v1_to_v0_revision_bridge,
)
from app.learning_engine.runtime import AlgoRuntimeProfile, get_bridge_config
from app.models.algo_runtime import (
    AlgoStateBridge,
    BanditThemeState,
    UserMasteryState,
    UserRevisionState,
    UserThemeStats,
)

logger = logging.getLogger(__name__)


async def ensure_user_bridged(
    user_id: UUID,
    from_profile: AlgoRuntimeProfile,
    to_profile: AlgoRuntimeProfile,
    policy_version: str,
    db: AsyncSession,
    now: datetime | None = None,
) -> None:
    """
    Ensure user state is bridged for the target profile (idempotent).

    Uses SELECT FOR UPDATE locking to prevent concurrent bridges.

    Args:
        user_id: User ID
        from_profile: Source profile
        to_profile: Target profile
        policy_version: Bridge policy version
        db: Database session
        now: Current timestamp (defaults to now)

    Raises:
        Exception: If bridge fails (logged but may be retried)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Get bridge config
    bridge_config_obj = await get_bridge_config(db, policy_version)
    if not bridge_config_obj:
        logger.error(f"Bridge config not found for policy_version={policy_version}")
        raise ValueError(f"Bridge config not found: {policy_version}")

    cfg = bridge_config_obj["config_json"]

    # Check or create bridge record with lock
    stmt = (
        select(AlgoStateBridge)
        .where(
            AlgoStateBridge.user_id == user_id,
            AlgoStateBridge.from_profile == from_profile,
            AlgoStateBridge.to_profile == to_profile,
            AlgoStateBridge.policy_version == policy_version,
        )
        .with_for_update()
    )
    result = await db.execute(stmt)
    bridge = result.scalar_one_or_none()

    if not bridge:
        # Create bridge record
        bridge = AlgoStateBridge(
            user_id=user_id,
            from_profile=from_profile,
            to_profile=to_profile,
            policy_version=policy_version,
            status="running",
            started_at=now,
        )
        db.add(bridge)
        await db.flush()
    elif bridge.status == "done":
        # Already bridged
        logger.debug(f"User {user_id} already bridged {from_profile.value} → {to_profile.value}")
        return
    elif bridge.status == "running":
        # Another process is running bridge - wait or skip
        logger.warning(f"Bridge already running for user {user_id}, skipping")
        return

    # Mark as running
    bridge.status = "running"
    bridge.started_at = now
    await db.flush()

    try:
        details = {
            "mastery_converted": 0,
            "revision_converted": 0,
            "bandit_converted": 0,
            "errors": [],
        }

        if to_profile == AlgoRuntimeProfile.V0_FALLBACK:
            # v1 → v0 bridge
            await _bridge_v1_to_v0(db, user_id, cfg, now, details)
        else:
            # v0 → v1 bridge
            await _bridge_v0_to_v1(db, user_id, cfg, now, details)

        # Mark as done
        bridge.status = "done"
        bridge.finished_at = datetime.now(timezone.utc)
        bridge.details_json = details

        await db.commit()

        logger.info(
            f"Bridged user {user_id} {from_profile.value} → {to_profile.value}: "
            f"{details['mastery_converted']} mastery, {details['revision_converted']} revision, "
            f"{details['bandit_converted']} bandit"
        )

    except Exception as e:
        logger.error(f"Bridge failed for user {user_id}: {e}")
        bridge.status = "failed"
        bridge.finished_at = datetime.now(timezone.utc)
        bridge.details_json = {"error": str(e)}
        await db.commit()
        raise


async def _bridge_v1_to_v0(
    db: AsyncSession,
    user_id: UUID,
    cfg: dict[str, Any],
    now: datetime,
    details: dict[str, Any],
) -> None:
    """Bridge v1 state to v0."""
    # Get all mastery states
    stmt = select(UserMasteryState).where(UserMasteryState.user_id == user_id)
    result = await db.execute(stmt)
    mastery_states = result.scalars().all()

    for state in mastery_states:
        # Ensure mastery_score exists
        if state.mastery_score is None or float(state.mastery_score) == 0:
            # Get theme stats
            stats_stmt = select(UserThemeStats).where(
                UserThemeStats.user_id == user_id,
                UserThemeStats.theme_id == state.theme_id,
            )
            stats_result = await db.execute(stats_stmt)
            stats = stats_result.scalar_one_or_none()

            if stats:
                mastery_score = compute_v0_mastery_from_aggregates(
                    stats.attempts_total,
                    stats.correct_total,
                    stats.last_attempt_at,
                    now,
                    cfg,
                )
                state.mastery_score = mastery_score
                state.mastery_model = "v0"
                details["mastery_converted"] += 1

    # Get all revision states
    stmt = select(UserRevisionState).where(UserRevisionState.user_id == user_id)
    result = await db.execute(stmt)
    revision_states = result.scalars().all()

    for state in revision_states:
        # Get theme stats
        stats_stmt = select(UserThemeStats).where(
            UserThemeStats.user_id == user_id,
            UserThemeStats.theme_id == state.theme_id,
        )
        stats_result = await db.execute(stats_stmt)
        stats = stats_result.scalar_one_or_none()

        stats_dict = None
        if stats:
            stats_dict = {
                "attempts_total": stats.attempts_total,
                "correct_total": stats.correct_total,
                "last_attempt_at": stats.last_attempt_at,
            }

        # Bridge revision state (pass datetime objects directly)
        state_dict = {
            "due_at": state.due_at,
            "last_review_at": state.last_review_at,
            "v0_interval_days": state.v0_interval_days,
            "v0_stage": state.v0_stage,
        }

        updated = v1_to_v0_revision_bridge(state_dict, stats_dict, cfg, now)

        # Update state (only if fields changed)
        if updated.get("v0_interval_days") is not None and state.v0_interval_days is None:
            state.v0_interval_days = updated["v0_interval_days"]
            details["revision_converted"] += 1
        if updated.get("v0_stage") is not None and state.v0_stage is None:
            state.v0_stage = updated["v0_stage"]


async def _bridge_v0_to_v1(
    db: AsyncSession,
    user_id: UUID,
    cfg: dict[str, Any],
    now: datetime,
    details: dict[str, Any],
) -> None:
    """Bridge v0 state to v1."""
    # Get all mastery states
    stmt = select(UserMasteryState).where(UserMasteryState.user_id == user_id)
    result = await db.execute(stmt)
    mastery_states = result.scalars().all()

    for state in mastery_states:
        # Initialize BKT if missing
        if state.mastery_score is not None and state.bkt_p_mastered is None:
            # Get theme stats for attempts_total
            stats_stmt = select(UserThemeStats).where(
                UserThemeStats.user_id == user_id,
                UserThemeStats.theme_id == state.theme_id,
            )
            stats_result = await db.execute(stats_stmt)
            stats = stats_result.scalar_one_or_none()

            attempts_total = stats.attempts_total if stats else 0
            p_prior = 0.5  # Default BKT prior

            bkt_p, bkt_state = init_bkt_from_mastery(
                float(state.mastery_score),
                p_prior,
                attempts_total,
                cfg,
            )

            state.bkt_p_mastered = bkt_p
            state.bkt_state_json = bkt_state
            state.mastery_model = "v1"
            details["mastery_converted"] += 1

    # Get all revision states
    stmt = select(UserRevisionState).where(UserRevisionState.user_id == user_id)
    result = await db.execute(stmt)
    revision_states = result.scalars().all()

    for state in revision_states:
        # Get theme stats
        stats_stmt = select(UserThemeStats).where(
            UserThemeStats.user_id == user_id,
            UserThemeStats.theme_id == state.theme_id,
        )
        stats_result = await db.execute(stats_stmt)
        stats = stats_result.scalar_one_or_none()

        stats_dict = None
        if stats:
            stats_dict = {
                "attempts_total": stats.attempts_total,
                "correct_total": stats.correct_total,
                "last_attempt_at": stats.last_attempt_at,
            }

        # Bridge revision state
        state_dict = {
            "due_at": state.due_at,
            "last_review_at": state.last_review_at,
            "stability": float(state.stability) if state.stability else None,
            "difficulty": float(state.difficulty) if state.difficulty else None,
            "v0_interval_days": state.v0_interval_days,
        }

        updated = v0_to_v1_revision_bridge(state_dict, stats_dict, cfg, now)

        # Update state (only if fields changed)
        if updated.get("stability") is not None and state.stability is None:
            state.stability = updated["stability"]
            details["revision_converted"] += 1
        if updated.get("difficulty") is not None and state.difficulty is None:
            state.difficulty = updated["difficulty"]
        if updated.get("due_at") and state.due_at is None:
            # due_at is already a datetime object from the bridge function
            if isinstance(updated["due_at"], datetime):
                state.due_at = updated["due_at"]
            elif isinstance(updated["due_at"], str):
                state.due_at = datetime.fromisoformat(updated["due_at"].replace("Z", "+00:00"))

    # Initialize bandit priors
    stmt = select(BanditThemeState).where(BanditThemeState.user_id == user_id)
    result = await db.execute(stmt)
    bandit_states = result.scalars().all()

    # Get mastery states for bandit initialization
    mastery_by_theme = {s.theme_id: s for s in mastery_states}

    for state in bandit_states:
        if state.alpha == 1.0 and state.beta == 1.0:  # Default prior
            mastery_state = mastery_by_theme.get(state.theme_id)
            if mastery_state and mastery_state.mastery_score:
                # Get attempts_total
                stats_stmt = select(UserThemeStats).where(
                    UserThemeStats.user_id == user_id,
                    UserThemeStats.theme_id == state.theme_id,
                )
                stats_result = await db.execute(stats_stmt)
                stats = stats_result.scalar_one_or_none()

                attempts_total = stats.attempts_total if stats else 0

                alpha, beta = init_bandit_beta_from_mastery(
                    float(mastery_state.mastery_score),
                    attempts_total,
                    cfg,
                )

                state.alpha = alpha
                state.beta = beta
                state.init_from = "mastery"
                state.policy_version = "ALGO_BRIDGE_SPEC_v1"
                details["bandit_converted"] += 1
