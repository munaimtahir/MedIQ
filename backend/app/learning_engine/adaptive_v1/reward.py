"""
Reward computation for Adaptive Selection v1 bandit learning.

Integrates with session submit to update Beta posteriors based on
learning outcomes measured by BKT mastery delta.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.adaptive_v1.core import (
    compute_bkt_delta_reward,
    update_beta_posterior,
)
from app.learning_engine.adaptive_v1.repo import (
    get_bandit_states_batch,
    upsert_bandit_state,
)
from app.learning_engine.config import get_adaptive_v1_defaults
from app.learning_engine.constants import AlgoKey
from app.learning_engine.registry import resolve_active
from app.models.adaptive import AdaptiveSelectionLog
from app.models.bkt import BKTUserSkillState
from app.models.question_cms import Question
from app.models.session import SessionAnswer, SessionQuestion, TestSession

logger = logging.getLogger(__name__)


async def compute_session_theme_attempts(
    db: AsyncSession,
    session_id: UUID,
) -> dict[int, int]:
    """
    Compute attempts per theme for a session.

    Args:
        db: Database session
        session_id: Session ID

    Returns:
        Dict mapping theme_id -> attempt count
    """
    # Get session questions with theme info
    query = (
        select(Question.theme_id, SessionAnswer.question_id)
        .join(SessionAnswer, SessionAnswer.question_id == Question.id)
        .where(SessionAnswer.session_id == session_id)
    )

    result = await db.execute(query)
    rows = result.all()

    # Count by theme
    theme_counts: dict[int, int] = {}
    for row in rows:
        theme_id = row.theme_id
        if theme_id is not None:
            theme_counts[theme_id] = theme_counts.get(theme_id, 0) + 1

    return theme_counts


async def compute_theme_mastery_snapshots(
    db: AsyncSession,
    user_id: UUID,
    theme_ids: list[int],
) -> dict[int, float]:
    """
    Compute current BKT mastery per theme.

    Aggregates concept-level mastery to theme level.

    Args:
        db: Database session
        user_id: User ID
        theme_ids: Theme IDs to compute

    Returns:
        Dict mapping theme_id -> average mastery
    """
    # Get all user skill states
    query = select(BKTUserSkillState).where(BKTUserSkillState.user_id == user_id)
    result = await db.execute(query)
    states = result.scalars().all()

    # For now, without concept->theme mapping, return default
    # In production, you'd join with concept->theme table
    mastery: dict[int, float] = {tid: 0.5 for tid in theme_ids}

    # If we have states, compute average (placeholder logic)
    if states:
        avg_mastery = sum(s.p_mastery for s in states) / len(states)
        for tid in theme_ids:
            mastery[tid] = avg_mastery

    return mastery


async def get_pre_session_mastery_from_log(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
) -> dict[int, float] | None:
    """
    Get pre-session mastery from selection log (if available).

    The selection log captures theme mastery at selection time,
    which serves as the "pre" snapshot for reward computation.

    Args:
        db: Database session
        session_id: Session ID
        user_id: User ID

    Returns:
        Dict mapping theme_id -> pre-mastery, or None if not found
    """
    # Find the most recent selection log for this user before session started
    session = await db.get(TestSession, session_id)
    if not session:
        return None

    query = (
        select(AdaptiveSelectionLog)
        .where(
            and_(
                AdaptiveSelectionLog.user_id == user_id,
                AdaptiveSelectionLog.requested_at <= session.started_at,
            )
        )
        .order_by(AdaptiveSelectionLog.requested_at.desc())
        .limit(1)
    )

    result = await db.execute(query)
    log = result.scalar_one_or_none()

    if not log or not log.candidates_json:
        return None

    # Extract mastery from candidates
    pre_mastery: dict[int, float] = {}
    for candidate in log.candidates_json:
        if isinstance(candidate, dict):
            theme_id = candidate.get("theme_id")
            mastery = candidate.get("mastery")
            if theme_id is not None and mastery is not None:
                pre_mastery[theme_id] = mastery

    return pre_mastery


async def update_bandit_rewards_on_session_submit(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    """
    Update bandit rewards after session submission.

    This is the main integration point called from the session submit flow.
    It:
    1. Computes attempts per theme
    2. Gets pre-session mastery (from selection log or current)
    3. Computes post-session mastery
    4. Updates Beta posteriors based on reward = normalized mastery delta

    Args:
        db: Database session
        session_id: Submitted session ID
        user_id: User ID

    Returns:
        Summary of reward updates
    """
    try:
        # Get params
        version, params_obj = await resolve_active(db, AlgoKey.ADAPTIVE_V1.value)
        if params_obj:
            params = {**get_adaptive_v1_defaults(), **(params_obj.params_json or {})}
        else:
            params = get_adaptive_v1_defaults()

        min_attempts = params.get("reward_min_attempts_per_theme", 3)

        # Step 1: Compute attempts per theme
        theme_attempts = await compute_session_theme_attempts(db, session_id)

        if not theme_attempts:
            logger.debug(f"No theme attempts found for session {session_id}")
            return {"session_id": str(session_id), "updates": [], "themes_updated": 0}

        theme_ids = list(theme_attempts.keys())

        # Step 2: Get pre-session mastery
        pre_mastery = await get_pre_session_mastery_from_log(db, session_id, user_id)
        if not pre_mastery:
            # Fallback: use current mastery as pre (less accurate but works)
            pre_mastery = await compute_theme_mastery_snapshots(db, user_id, theme_ids)

        # Step 3: Compute post-session mastery (current state)
        post_mastery = await compute_theme_mastery_snapshots(db, user_id, theme_ids)

        # Step 4: Get current bandit states
        bandit_states = await get_bandit_states_batch(db, user_id, theme_ids)

        # Step 5: Compute rewards and update posteriors
        now = datetime.now(UTC)
        updates = []

        for theme_id, n_attempts in theme_attempts.items():
            if n_attempts < min_attempts:
                logger.debug(
                    f"Skipping reward update for theme {theme_id}: "
                    f"{n_attempts} attempts < min {min_attempts}"
                )
                continue

            pre = pre_mastery.get(theme_id, 0.5)
            post = post_mastery.get(theme_id, 0.5)

            # Compute normalized reward
            reward = compute_bkt_delta_reward(pre, post)

            # Get current state
            state = bandit_states.get(theme_id)
            if state:
                old_a, old_b = state.a, state.b
                n_sessions = state.n_sessions
                last_selected = state.last_selected_at
            else:
                old_a = params.get("beta_prior_a", 1.0)
                old_b = params.get("beta_prior_b", 1.0)
                n_sessions = 0
                last_selected = now

            # Update Beta posterior
            new_a, new_b = update_beta_posterior(old_a, old_b, reward)

            # Upsert state
            await upsert_bandit_state(
                db,
                user_id=user_id,
                theme_id=theme_id,
                a=new_a,
                b=new_b,
                n_sessions=n_sessions,
                last_selected_at=last_selected,
                last_reward=reward,
            )

            updates.append(
                {
                    "theme_id": theme_id,
                    "n_attempts": n_attempts,
                    "reward": round(reward, 4),
                    "pre_mastery": round(pre, 4),
                    "post_mastery": round(post, 4),
                    "delta": round(post - pre, 4),
                    "old_a": round(old_a, 4),
                    "old_b": round(old_b, 4),
                    "new_a": round(new_a, 4),
                    "new_b": round(new_b, 4),
                }
            )

        await db.commit()

        logger.info(f"Updated bandit rewards for session {session_id}: {len(updates)} themes")

        return {
            "session_id": str(session_id),
            "updates": updates,
            "themes_updated": len(updates),
        }

    except Exception as e:
        logger.error(f"Failed to update bandit rewards for session {session_id}: {e}")
        # Don't fail the session submit - reward update is best-effort
        return {
            "session_id": str(session_id),
            "error": str(e),
            "updates": [],
            "themes_updated": 0,
        }


async def get_user_bandit_summary(
    db: AsyncSession,
    user_id: UUID,
) -> dict[str, Any]:
    """
    Get summary of user's bandit state across themes.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Summary with theme states and statistics
    """
    from app.models.adaptive import BanditUserThemeState

    query = (
        select(BanditUserThemeState)
        .where(BanditUserThemeState.user_id == user_id)
        .order_by(BanditUserThemeState.last_selected_at.desc())
    )

    result = await db.execute(query)
    states = result.scalars().all()

    if not states:
        return {
            "user_id": str(user_id),
            "themes": [],
            "total_themes": 0,
            "total_sessions": 0,
        }

    theme_summaries = []
    total_sessions = 0

    for state in states:
        # Compute expected value (mean of Beta)
        expected = state.a / (state.a + state.b)

        theme_summaries.append(
            {
                "theme_id": state.theme_id,
                "a": round(state.a, 3),
                "b": round(state.b, 3),
                "expected_yield": round(expected, 4),
                "n_sessions": state.n_sessions,
                "last_reward": round(state.last_reward, 4) if state.last_reward else None,
                "last_selected_at": state.last_selected_at.isoformat()
                if state.last_selected_at
                else None,
            }
        )
        total_sessions += state.n_sessions

    return {
        "user_id": str(user_id),
        "themes": theme_summaries,
        "total_themes": len(theme_summaries),
        "total_sessions": total_sessions,
    }
