"""State adapters for v0 ⇄ v1 bridging.

These adapters ensure seamless transitions between algorithm versions
by converting state in a way that preserves student progress.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.algo_runtime import (
    AlgoStateBridge,
    UserMasteryState,
    UserRevisionState,
    UserThemeStats,
)

logger = logging.getLogger(__name__)


async def bridge_v1_to_v0(
    db: AsyncSession,
    user_id: UUID,
    force: bool = False,
) -> dict[str, Any]:
    """
    Bridge v1 state to v0 (when falling back to v0).

    Converts:
    - BKT mastery → canonical mastery_score (preserved)
    - FSRS revision state → v0 interval/stage (derived from due_at)
    - Preserves canonical aggregates

    Args:
        db: Database session
        user_id: User ID
        force: If True, re-run even if already bridged

    Returns:
        Bridge result with counts and status
    """
    # Check if already bridged
    if not force:
        stmt = select(AlgoStateBridge).where(
            AlgoStateBridge.user_id == user_id,
            AlgoStateBridge.from_profile == "V1_PRIMARY",
            AlgoStateBridge.to_profile == "V0_FALLBACK",
            AlgoStateBridge.status == "done",
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"User {user_id} already bridged v1→v0, skipping")
            return {"status": "skipped", "reason": "already_bridged"}

    # Create bridge record
    bridge = AlgoStateBridge(
        user_id=user_id,
        from_profile="V1_PRIMARY",
        to_profile="V0_FALLBACK",
        status="running",
    )
    db.add(bridge)
    await db.flush()

    try:
        # 1. Mastery: Use canonical mastery_score (already populated by v1)
        # v0 can use mastery_score directly, no conversion needed
        mastery_count = 0
        stmt = select(UserMasteryState).where(UserMasteryState.user_id == user_id)
        result = await db.execute(stmt)
        mastery_states = result.scalars().all()
        for state in mastery_states:
            # Ensure mastery_score is populated (v1 should have written it)
            if state.mastery_score is None or float(state.mastery_score) == 0:
                # Fallback: compute from user_theme_stats
                stats = await _get_theme_stats(db, user_id, state.theme_id)
                if stats:
                    accuracy = (
                        float(stats.correct_total) / stats.attempts_total
                        if stats.attempts_total > 0
                        else 0.0
                    )
                    state.mastery_score = accuracy
                    state.mastery_model = "v0"
                    mastery_count += 1

        # 2. Revision: Derive v0 state from canonical due_at
        revision_count = 0
        stmt = select(UserRevisionState).where(UserRevisionState.user_id == user_id)
        result = await db.execute(stmt)
        revision_states = result.scalars().all()
        for state in revision_states:
            if state.due_at:
                # Derive v0_interval_days from time until due
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc)
                if state.due_at > now:
                    days_until_due = (state.due_at - now).days
                    state.v0_interval_days = max(1, days_until_due)
                    # Derive v0_stage from interval (simple mapping)
                    if state.v0_interval_days <= 1:
                        state.v0_stage = 1
                    elif state.v0_interval_days <= 3:
                        state.v0_stage = 2
                    elif state.v0_interval_days <= 7:
                        state.v0_stage = 3
                    else:
                        state.v0_stage = 4
                    revision_count += 1

        await db.commit()

        bridge.status = "done"
        bridge.finished_at = datetime.now(timezone.utc)
        bridge.details_json = {
            "mastery_converted": mastery_count,
            "revision_converted": revision_count,
            "notes": "v1→v0 bridge completed. Canonical state preserved.",
        }

        await db.commit()

        logger.info(f"Bridged v1→v0 for user {user_id}: {mastery_count} mastery, {revision_count} revision")

        return {
            "status": "done",
            "mastery_converted": mastery_count,
            "revision_converted": revision_count,
        }

    except Exception as e:
        logger.error(f"Bridge v1→v0 failed for user {user_id}: {e}")
        bridge.status = "failed"
        bridge.finished_at = datetime.now(timezone.utc)
        bridge.details_json = {"error": str(e)}
        await db.commit()
        raise


async def bridge_v0_to_v1(
    db: AsyncSession,
    user_id: UUID,
    force: bool = False,
) -> dict[str, Any]:
    """
    Bridge v0 state to v1 (when returning to v1).

    Converts:
    - Canonical mastery_score → BKT initialization (non-trivial priors)
    - v0 revision state → FSRS stability/difficulty (mapped from interval)
    - Preserves canonical aggregates

    Args:
        db: Database session
        user_id: User ID
        force: If True, re-run even if already bridged

    Returns:
        Bridge result with counts and status
    """
    # Check if already bridged
    if not force:
        stmt = select(AlgoStateBridge).where(
            AlgoStateBridge.user_id == user_id,
            AlgoStateBridge.from_profile == "V0_FALLBACK",
            AlgoStateBridge.to_profile == "V1_PRIMARY",
            AlgoStateBridge.status == "done",
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"User {user_id} already bridged v0→v1, skipping")
            return {"status": "skipped", "reason": "already_bridged"}

    # Create bridge record
    bridge = AlgoStateBridge(
        user_id=user_id,
        from_profile="V0_FALLBACK",
        to_profile="V1_PRIMARY",
        status="running",
    )
    db.add(bridge)
    await db.flush()

    try:
        from datetime import datetime, timezone

        # 1. Mastery: Initialize BKT from canonical mastery_score
        mastery_count = 0
        stmt = select(UserMasteryState).where(UserMasteryState.user_id == user_id)
        result = await db.execute(stmt)
        mastery_states = result.scalars().all()

        for state in mastery_states:
            # Get theme stats for BKT initialization
            stats = await _get_theme_stats(db, user_id, state.theme_id)
            if stats and stats.attempts_total > 0:
                # Initialize BKT p_mastered from mastery_score (bounded)
                mastery_val = float(state.mastery_score) if state.mastery_score else 0.0
                # Bound to reasonable range for BKT
                bkt_p = max(0.1, min(0.9, mastery_val))
                state.bkt_p_mastered = bkt_p

                # Initialize BKT state from aggregates
                state.bkt_state_json = {
                    "p_L0": bkt_p,  # Prior from mastery_score
                    "n_attempts": stats.attempts_total,
                    "n_correct": stats.correct_total,
                    "initialized_from_v0": True,
                }
                state.mastery_model = "v1"
                mastery_count += 1

        # 2. Revision: Initialize FSRS from v0 state
        revision_count = 0
        stmt = select(UserRevisionState).where(UserRevisionState.user_id == user_id)
        result = await db.execute(stmt)
        revision_states = result.scalars().all()

        for state in revision_states:
            if state.v0_interval_days:
                # Map v0_interval_days to FSRS stability
                # Simple monotonic mapping (can be refined)
                interval = state.v0_interval_days
                # Stability roughly proportional to interval (with bounds)
                stability = min(30.0, max(1.0, interval * 1.5))
                state.stability = stability

                # Initialize difficulty from accuracy (if available)
                stats = await _get_theme_stats(db, user_id, state.theme_id)
                if stats and stats.attempts_total > 0:
                    accuracy = (
                        float(stats.correct_total) / stats.attempts_total
                        if stats.attempts_total > 0
                        else 0.5
                    )
                    # Difficulty inversely related to accuracy
                    difficulty = max(0.1, min(2.0, 1.0 - accuracy + 0.5))
                    state.difficulty = difficulty

                # Preserve due_at (canonical)
                if not state.due_at and state.v0_interval_days:
                    from datetime import timedelta

                    state.due_at = datetime.now(timezone.utc) + timedelta(days=state.v0_interval_days)

                revision_count += 1

        await db.commit()

        bridge.status = "done"
        bridge.finished_at = datetime.now(timezone.utc)
        bridge.details_json = {
            "mastery_converted": mastery_count,
            "revision_converted": revision_count,
            "notes": "v0→v1 bridge completed. BKT and FSRS initialized from canonical state.",
        }

        await db.commit()

        logger.info(f"Bridged v0→v1 for user {user_id}: {mastery_count} mastery, {revision_count} revision")

        return {
            "status": "done",
            "mastery_converted": mastery_count,
            "revision_converted": revision_count,
        }

    except Exception as e:
        logger.error(f"Bridge v0→v1 failed for user {user_id}: {e}")
        bridge.status = "failed"
        bridge.finished_at = datetime.now(timezone.utc)
        bridge.details_json = {"error": str(e)}
        await db.commit()
        raise


async def _get_theme_stats(db: AsyncSession, user_id: UUID, theme_id: int) -> UserThemeStats | None:
    """Get user theme stats."""
    stmt = select(UserThemeStats).where(
        UserThemeStats.user_id == user_id,
        UserThemeStats.theme_id == theme_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
