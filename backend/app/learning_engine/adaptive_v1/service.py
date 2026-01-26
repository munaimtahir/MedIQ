"""
Adaptive Selection v1 Service - Main orchestration layer.

Coordinates:
- Theme selection via constrained Thompson Sampling
- Question picking within themes
- Logging and run tracking
- Integration with existing learning engine infrastructure
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.adaptive_v1.core import (
    SelectionPlan,
    ThemeCandidate,
    compute_base_priority,
    compute_recency_penalty,
    create_deterministic_seed,
    normalize_uncertainty,
    run_theme_selection,
)
from app.learning_engine.adaptive_v1.question_picker import pick_questions_for_all_themes
from app.learning_engine.adaptive_v1.repo import (
    get_bandit_states_batch,
    get_bkt_mastery_by_theme,
    get_candidate_themes,
    get_due_concepts_by_theme,
    get_questions_for_theme,
    get_recently_seen_question_ids,
    get_theme_supply_batch,
    get_user_global_rating,
)
from app.learning_engine.config import get_adaptive_v1_defaults, get_elo_defaults
from app.learning_engine.constants import AlgoKey
from app.learning_engine.registry import resolve_active
from app.learning_engine.runs import log_run_failure, log_run_start, log_run_success
from app.models.adaptive import AdaptiveSelectionLog

logger = logging.getLogger(__name__)


async def select_questions_v1(
    db: AsyncSession,
    *,
    user_id: UUID,
    year: int,
    block_ids: list[int],
    theme_ids_filter: list[int] | None,
    count: int,
    mode: str,
    source: str = "mixed",
    trigger: str = "api",
) -> dict[str, Any]:
    """
    Select questions using Adaptive v1 (constrained Thompson Sampling).

    Full pipeline:
    1. Resolve active algorithm version and parameters
    2. Get candidate themes with supply counts
    3. Compute base priority features (BKT, FSRS, Elo, recency)
    4. Load bandit states (Beta posteriors)
    5. Run Thompson Sampling to select themes
    6. Allocate quotas to selected themes
    7. Pick questions within each theme
    8. Log selection to adaptive_selection_log
    9. Return ordered question_ids with metadata

    Args:
        db: Database session
        user_id: User ID
        year: Academic year
        block_ids: Block IDs to select from
        theme_ids_filter: Optional explicit theme filter
        count: Number of questions to select
        mode: Session mode (tutor, exam, revision)
        source: Selection source (mixed, revision, weakness)
        trigger: Run trigger source

    Returns:
        Dict with question_ids, plan, run_id, stats
    """
    now = datetime.now(UTC)
    run_id = uuid4()

    try:
        # Step 1: Resolve active algorithm version and parameters
        version, params_obj = await resolve_active(db, AlgoKey.ADAPTIVE_V1.value)

        # Fall back to adaptive key if v1 not configured
        if not version or not params_obj:
            version, params_obj = await resolve_active(db, AlgoKey.ADAPTIVE.value)

        if not version or not params_obj:
            logger.warning("No active adaptive algorithm configured, using defaults")
            params = get_adaptive_v1_defaults()
            version_id = None
            params_id = None
        else:
            params = {**get_adaptive_v1_defaults(), **(params_obj.params_json or {})}
            version_id = version.id
            params_id = params_obj.id

        # Merge Elo params for p(correct) computation
        elo_params = get_elo_defaults()
        params = {**params, **elo_params}

        # Log run start
        if version_id and params_id:
            run = await log_run_start(
                db,
                algo_version_id=version_id,
                params_id=params_id,
                user_id=user_id,
                session_id=None,
                trigger=trigger,
                input_summary={
                    "user_id": str(user_id),
                    "year": year,
                    "block_ids": block_ids,
                    "theme_ids_filter": theme_ids_filter,
                    "count": count,
                    "mode": mode,
                    "source": source,
                },
            )
            run_id = run.id

        # Step 2: Create deterministic seed
        seed = create_deterministic_seed(
            user_id=user_id,
            mode=mode,
            count=count,
            block_ids=block_ids,
            theme_ids=theme_ids_filter,
        )

        # Step 3: Get recently seen questions for exclusion
        exclude_days = params.get("exclude_seen_within_days", 14)
        exclude_sessions = params.get("exclude_seen_within_sessions", 3)
        excluded_question_ids = await get_recently_seen_question_ids(
            db, user_id, exclude_days, exclude_sessions
        )

        # Step 4: Get candidate themes
        max_candidates = params.get("max_candidate_themes", 30)
        raw_themes = await get_candidate_themes(
            db, user_id, year, block_ids, theme_ids_filter, max_candidates
        )

        if not raw_themes:
            logger.warning(f"No candidate themes found for user {user_id}")
            return {
                "question_ids": [],
                "count": 0,
                "run_id": str(run_id),
                "plan": {"themes": [], "total_quota": 0},
                "stats": {"error": "no_themes"},
            }

        theme_ids = [t["theme_id"] for t in raw_themes]

        # Step 5: Get supply counts for all themes
        theme_supply = await get_theme_supply_batch(db, theme_ids, excluded_question_ids)

        # Step 6: Get BKT mastery by theme
        theme_mastery = await get_bkt_mastery_by_theme(db, user_id, theme_ids)

        # Step 7: Get FSRS due concepts by theme
        due_by_theme = await get_due_concepts_by_theme(db, user_id, theme_ids, now)

        # Step 8: Get user global Elo rating
        user_rating, user_uncertainty = await get_user_global_rating(db, user_id)

        # Step 9: Get bandit states for all themes
        bandit_states = await get_bandit_states_batch(db, user_id, theme_ids)

        # Step 10: Build theme candidates with all features
        candidates: list[ThemeCandidate] = []
        for raw_theme in raw_themes:
            tid = raw_theme["theme_id"]

            # Get features
            mastery = theme_mastery.get(tid, 0.5)
            due_concepts = due_by_theme.get(tid, [])
            supply = theme_supply.get(tid, 0)

            # Compute due ratio (placeholder - needs proper concept count)
            due_ratio = len(due_concepts) / 10.0 if due_concepts else 0.0
            due_ratio = min(1.0, due_ratio)

            # Get bandit state
            state = bandit_states.get(tid)
            beta_a = state.a if state else params.get("beta_prior_a", 1.0)
            beta_b = state.b if state else params.get("beta_prior_b", 1.0)
            last_selected = state.last_selected_at if state else None

            # Compute recency penalty
            recency_penalty = compute_recency_penalty(last_selected, now)

            # Normalize user uncertainty for this theme
            unc_norm = normalize_uncertainty(
                user_uncertainty,
                params.get("unc_init_user", 350.0),
                params.get("unc_floor", 50.0),
            )

            # Create candidate
            candidate = ThemeCandidate(
                theme_id=tid,
                title=raw_theme["title"],
                block_id=raw_theme["block_id"],
                mastery=mastery,
                weakness=1.0 - mastery,
                due_ratio=due_ratio,
                uncertainty=unc_norm,
                recency_penalty=recency_penalty,
                supply=supply,
                beta_a=beta_a,
                beta_b=beta_b,
            )

            # Compute base priority
            candidate.base_priority = compute_base_priority(
                weakness=candidate.weakness,
                due_ratio=candidate.due_ratio,
                uncertainty=candidate.uncertainty,
                recency_penalty=candidate.recency_penalty,
                supply=candidate.supply,
                params=params,
            )

            candidates.append(candidate)

        # Step 11: Run theme selection (Thompson Sampling)
        plan: SelectionPlan = run_theme_selection(candidates, count, seed, params)

        selected_themes = plan.selected_themes()

        if not selected_themes:
            logger.warning(f"No themes selected for user {user_id}")
            return {
                "question_ids": [],
                "count": 0,
                "run_id": str(run_id),
                "plan": plan.to_dict(),
                "stats": {"error": "no_themes_selected"},
            }

        # Step 12: Get questions for selected themes
        questions_by_theme: dict[int, list[dict]] = {}
        for theme in selected_themes:
            questions = await get_questions_for_theme(
                db, theme.theme_id, excluded_question_ids, limit=100
            )
            questions_by_theme[theme.theme_id] = questions

        # Step 13: Pick questions
        theme_quotas = [(t.theme_id, t.quota) for t in selected_themes]

        # Get due and weak concept IDs for picking (placeholder - needs proper mapping)
        due_concept_ids: set[int] = set()
        weak_concept_ids: set[int] = set()
        for tid, due_list in due_by_theme.items():
            for concept_id in due_list:
                # Convert UUID to int if needed
                if isinstance(concept_id, int):
                    due_concept_ids.add(concept_id)

        question_ids, picker_stats = pick_questions_for_all_themes(
            theme_quotas=theme_quotas,
            questions_by_theme=questions_by_theme,
            user_rating=user_rating,
            due_concept_ids=due_concept_ids,
            weak_concept_ids=weak_concept_ids,
            params=params,
            seed=seed,
            interleave=(mode != "exam"),  # Don't interleave in exam mode
        )

        # Step 14: Write selection log
        selection_log = AdaptiveSelectionLog(
            id=uuid4(),
            user_id=user_id,
            requested_at=now,
            mode=mode,
            source=source,
            year=year,
            block_ids=block_ids,
            theme_ids_filter=theme_ids_filter,
            count=count,
            seed=seed,
            algo_version_id=version_id,
            params_id=params_id,
            run_id=run_id,
            candidates_json=[c.to_dict() for c in candidates],
            selected_json=[t.to_dict() for t in selected_themes],
            question_ids_json=[str(q) for q in question_ids],
            stats_json=picker_stats,
        )
        db.add(selection_log)
        await db.flush()

        # Step 15: Update bandit states (mark as selected)
        for theme in selected_themes:
            state = bandit_states.get(theme.theme_id)
            if state:
                state.last_selected_at = now
                state.n_sessions += 1
                state.updated_at = now
                db.add(state)
            else:
                # Create new state
                from app.models.adaptive import BanditUserThemeState

                new_state = BanditUserThemeState(
                    user_id=user_id,
                    theme_id=theme.theme_id,
                    a=params.get("beta_prior_a", 1.0),
                    b=params.get("beta_prior_b", 1.0),
                    n_sessions=1,
                    last_selected_at=now,
                    updated_at=now,
                )
                db.add(new_state)

        await db.commit()

        # Step 16: Log run success
        if version_id and params_id:
            await log_run_success(
                db,
                run_id=run_id,
                output_summary={
                    "count": len(question_ids),
                    "themes_used": len(selected_themes),
                    "avg_p_correct": picker_stats.get("avg_p_correct", 0.0),
                },
            )

        # Build response
        plan_dict = {
            "themes": [
                {
                    "theme_id": t.theme_id,
                    "quota": t.quota,
                    "base_priority": round(t.base_priority, 4),
                    "sampled_y": round(t.sampled_y, 4),
                    "final_score": round(t.final_score, 4),
                }
                for t in selected_themes
            ],
            "due_ratio": picker_stats.get("due_coverage", 0) / max(1, len(question_ids)),
            "p_band": {"low": params.get("p_low", 0.55), "high": params.get("p_high", 0.80)},
            "stats": {
                "excluded_recent": len(excluded_question_ids),
                "explore_used": picker_stats.get("explore_count", 0),
                "avg_p_correct": picker_stats.get("avg_p_correct", 0.0),
            },
        }

        return {
            "question_ids": question_ids,
            "count": len(question_ids),
            "run_id": str(run_id),
            "algo": {
                "key": AlgoKey.ADAPTIVE_V1.value if version_id else "adaptive",
                "version": version.version if version else "v1",
            },
            "params_id": str(params_id) if params_id else None,
            "plan": plan_dict,
        }

    except Exception as e:
        logger.error(f"Adaptive selection v1 failed for user {user_id}: {e}", exc_info=True)

        # Log failure if run was started
        if version_id and params_id and "run" in locals():
            await log_run_failure(db, run_id=run_id, error_message=str(e))

        return {
            "question_ids": [],
            "count": 0,
            "run_id": str(run_id),
            "error": str(e),
        }


async def update_bandit_rewards_for_session(
    db: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
    theme_attempts: dict[int, int],
    pre_mastery: dict[int, float],
    post_mastery: dict[int, float],
) -> dict[str, Any]:
    """
    Update bandit rewards after session completion.

    Called after session submit to update Beta posteriors based on
    learning outcomes measured by BKT mastery delta.

    Args:
        db: Database session
        user_id: User ID
        session_id: Completed session ID
        theme_attempts: Dict mapping theme_id -> number of attempts
        pre_mastery: Dict mapping theme_id -> mastery before session
        post_mastery: Dict mapping theme_id -> mastery after session

    Returns:
        Summary of reward updates
    """
    from app.learning_engine.adaptive_v1.core import (
        compute_bkt_delta_reward,
        update_beta_posterior,
    )
    from app.learning_engine.adaptive_v1.repo import get_bandit_states_batch, upsert_bandit_state

    now = datetime.now(UTC)

    # Get params
    version, params_obj = await resolve_active(db, AlgoKey.ADAPTIVE_V1.value)
    if params_obj:
        params = {**get_adaptive_v1_defaults(), **(params_obj.params_json or {})}
    else:
        params = get_adaptive_v1_defaults()

    min_attempts = params.get("reward_min_attempts_per_theme", 3)

    # Get current bandit states
    theme_ids = list(theme_attempts.keys())
    states = await get_bandit_states_batch(db, user_id, theme_ids)

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

        # Compute reward
        reward = compute_bkt_delta_reward(pre, post)

        # Get current state
        state = states.get(theme_id)
        if state:
            old_a, old_b = state.a, state.b
            n_sessions = state.n_sessions
        else:
            old_a = params.get("beta_prior_a", 1.0)
            old_b = params.get("beta_prior_b", 1.0)
            n_sessions = 0

        # Update posterior
        new_a, new_b = update_beta_posterior(old_a, old_b, reward)

        # Upsert state
        await upsert_bandit_state(
            db,
            user_id=user_id,
            theme_id=theme_id,
            a=new_a,
            b=new_b,
            n_sessions=n_sessions,  # Don't increment here, already done at selection time
            last_selected_at=state.last_selected_at if state else now,
            last_reward=reward,
        )

        updates.append(
            {
                "theme_id": theme_id,
                "reward": round(reward, 4),
                "pre_mastery": round(pre, 4),
                "post_mastery": round(post, 4),
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
