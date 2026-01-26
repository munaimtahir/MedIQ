"""Graph-aware revision planner v1.

Re-ranks and augments FSRS revision plans using prerequisite graph knowledge.
Shadow-first: produces shadow plans that don't affect student queues unless activated.
"""

import logging
from datetime import date, datetime, UTC
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.neo4j_client import is_neo4j_available
from app.graph.service import get_prereqs
from app.learning_engine.runtime import is_safe_mode_freeze_updates
from app.models.algo_runtime import UserMasteryState, UserRevisionState
from app.models.graph_revision import GraphRevisionConfig, ShadowRevisionPlan

logger = logging.getLogger(__name__)


async def get_planner_config(db: AsyncSession) -> dict[str, Any]:
    """
    Get graph revision planner configuration.

    Args:
        db: Database session

    Returns:
        Configuration dictionary with default values
    """
    stmt = select(GraphRevisionConfig).where(
        GraphRevisionConfig.policy_version == "graph_revision_v1"
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config and config.config_json:
        return config.config_json

    # Default config
    return {
        "prereq_depth": 2,
        "injection_cap_ratio": 0.25,
        "max_prereq_per_theme": 2,
        "scoring_weights": {
            "mastery_inverse": 0.5,
            "is_overdue": 0.3,
            "recency_need": 0.2,
        },
    }


async def compute_shadow_revision_plan(
    db: AsyncSession,
    user_id: UUID,
    baseline_due_themes: list[int],  # List of theme_ids due from FSRS
    run_date: date,
) -> ShadowRevisionPlan | None:
    """
    Compute shadow revision plan (augmented with prerequisites).

    This function:
    1. Takes baseline due themes from FSRS
    2. Fetches prerequisites for each due theme
    3. Scores and selects top prerequisites to inject
    4. Produces ordered plan (baseline + injected prereqs)
    5. Stores in shadow_revision_plan (if not frozen)

    Args:
        db: Database session
        user_id: User ID
        baseline_due_themes: List of theme IDs due from FSRS
        run_date: Date for which plan is computed

    Returns:
        ShadowRevisionPlan if computed, None if blocked (frozen/disabled)
    """
    # Check freeze mode
    if await is_safe_mode_freeze_updates(db):
        logger.info(f"Shadow revision plan blocked: freeze_updates mode enabled for user {user_id}")
        return None

    # Check Neo4j availability
    if not is_neo4j_available():
        logger.info(f"Neo4j unavailable, returning baseline-only plan for user {user_id}")
        plan = ShadowRevisionPlan(
            user_id=user_id,
            run_date=run_date,
            mode="baseline",
            baseline_count=len(baseline_due_themes),
            injected_count=0,
            plan_json=[{"theme_id": tid, "kind": "due", "reason_codes": ["baseline"]} for tid in baseline_due_themes],
            computed_at=datetime.now(UTC),
        )
        db.add(plan)
        await db.commit()
        return plan

    # Get planner config
    config = await get_planner_config(db)
    prereq_depth = config.get("prereq_depth", 2)
    injection_cap_ratio = config.get("injection_cap_ratio", 0.25)
    max_prereq_per_theme = config.get("max_prereq_per_theme", 2)
    scoring_weights = config.get("scoring_weights", {})

    # Get user mastery and revision state
    mastery_stmt = select(UserMasteryState).where(UserMasteryState.user_id == user_id)
    mastery_result = await db.execute(mastery_stmt)
    mastery_states = {ms.theme_id: ms for ms in mastery_result.scalars().all()}

    revision_stmt = select(UserRevisionState).where(UserRevisionState.user_id == user_id)
    revision_result = await db.execute(revision_stmt)
    revision_states = {rs.theme_id: rs for rs in revision_result.scalars().all()}

    # Build plan: start with baseline due themes
    plan_items = []
    for theme_id in baseline_due_themes:
        plan_items.append({
            "theme_id": theme_id,
            "kind": "due",
            "reason_codes": ["baseline"],
        })

    # For each due theme, fetch prerequisites and score them
    prereq_candidates: dict[int, dict[str, Any]] = {}  # theme_id -> candidate data

    for due_theme_id in baseline_due_themes:
        try:
            prereq_ids = get_prereqs(due_theme_id, depth=prereq_depth, max_nodes=50)
            # Limit to max_prereq_per_theme
            prereq_ids = prereq_ids[:max_prereq_per_theme]

            for prereq_id in prereq_ids:
                # Skip if already in baseline
                if prereq_id in baseline_due_themes:
                    continue

                # Skip if already considered
                if prereq_id in prereq_candidates:
                    prereq_candidates[prereq_id]["source_themes"].append(due_theme_id)
                    continue

                # Score this prerequisite
                mastery_state = mastery_states.get(prereq_id)
                revision_state = revision_states.get(prereq_id)

                mastery_score = float(mastery_state.mastery_score) if mastery_state else 0.0
                is_overdue = False
                recency_need = 0.0

                if revision_state:
                    if revision_state.due_at:
                        is_overdue = revision_state.due_at.date() < run_date
                    if revision_state.last_reviewed_at:
                        days_since = (run_date - revision_state.last_reviewed_at.date()).days
                        recency_need = min(days_since / 30.0, 1.0)  # Normalize to 0..1

                # Compute score
                score = (
                    (1.0 - mastery_score) * scoring_weights.get("mastery_inverse", 0.5)
                    + (1.0 if is_overdue else 0.0) * scoring_weights.get("is_overdue", 0.3)
                    + recency_need * scoring_weights.get("recency_need", 0.2)
                )

                prereq_candidates[prereq_id] = {
                    "theme_id": prereq_id,
                    "score": score,
                    "mastery_score": mastery_score,
                    "is_overdue": is_overdue,
                    "recency_need": recency_need,
                    "source_themes": [due_theme_id],
                    "reason_codes": ["prereq_injection"],
                }

        except Exception as e:
            logger.warning(f"Error fetching prerequisites for theme {due_theme_id}: {e}")
            continue

    # Select top prerequisites (respecting injection cap)
    injection_cap = max(1, int(len(baseline_due_themes) * injection_cap_ratio))
    sorted_prereqs = sorted(prereq_candidates.values(), key=lambda x: x["score"], reverse=True)
    selected_prereqs = sorted_prereqs[:injection_cap]

    # Add selected prerequisites to plan (inserted after their source themes)
    # For simplicity, append at end (can be refined to insert near source)
    for prereq in selected_prereqs:
        plan_items.append({
            "theme_id": prereq["theme_id"],
            "kind": "prereq",
            "score": prereq["score"],
            "reason_codes": prereq["reason_codes"] + [f"source:{sid}" for sid in prereq["source_themes"]],
            "mastery_score": prereq["mastery_score"],
            "is_overdue": prereq["is_overdue"],
        })

    # Create shadow plan
    plan = ShadowRevisionPlan(
        user_id=user_id,
        run_date=run_date,
        mode="shadow",
        baseline_count=len(baseline_due_themes),
        injected_count=len(selected_prereqs),
        plan_json=plan_items,
        computed_at=datetime.now(UTC),
    )

    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    logger.info(
        f"Shadow revision plan computed for user {user_id}: "
        f"{len(baseline_due_themes)} baseline, {len(selected_prereqs)} injected"
    )

    return plan
