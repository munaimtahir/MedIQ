"""BKT suite implementation for evaluation harness."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.bkt.core import predict_correct, posterior_given_obs
from app.learning_engine.eval.replay import EvalSuite, ReplayPrediction, ReplayState
from app.learning_engine.eval.dataset import EvalEvent
from app.learning_engine.tag_quality import get_concept_id_with_fallback
from app.models.bkt import BKTSkillParams, BKTUserSkillState

logger = logging.getLogger(__name__)


class BKTEvalSuite(EvalSuite):
    """BKT suite for evaluation replay."""

    def __init__(self, db: AsyncSession):
        """Initialize BKT suite with database session."""
        self.db = db

    async def predict(self, state: ReplayState, event_context: EvalEvent) -> ReplayPrediction:
        """Compute BKT predictions before state update."""
        # Get BKT state for this concept
        concept_id, tag_debt = await get_concept_id_with_fallback(
            self.db, event_context.question_id, event_context.theme_id
        )

        # Get user skill state
        stmt = select(BKTUserSkillState).where(
            BKTUserSkillState.user_id == state.user_id,
            BKTUserSkillState.concept_id == concept_id,
        )
        result = await self.db.execute(stmt)
        skill_state = result.scalar_one_or_none()

        if not skill_state:
            # No state yet, use default
            p_mastery = 0.1  # Default L0
            p_correct = None
        else:
            # Get skill params
            stmt = select(BKTSkillParams).where(
                BKTSkillParams.concept_id == concept_id,
                BKTSkillParams.is_active == True,  # noqa: E712
            )
            result = await self.db.execute(stmt)
            skill_params = result.scalar_one_or_none()

            if skill_params:
                p_mastery = float(skill_state.p_mastery)
                p_correct = predict_correct(
                    p_mastery,
                    float(skill_params.p_S),
                    float(skill_params.p_G),
                )
            else:
                # Use defaults
                from app.learning_engine.config import (
                    BKT_DEFAULT_G,
                    BKT_DEFAULT_L0,
                    BKT_DEFAULT_S,
                )

                p_mastery = float(skill_state.p_mastery) if skill_state else BKT_DEFAULT_L0.value
                p_correct = predict_correct(
                    p_mastery,
                    BKT_DEFAULT_S.value,
                    BKT_DEFAULT_G.value,
                )

        return ReplayPrediction(
            event_id=getattr(event_context, "event_id", None),
            p_correct=p_correct,
            p_mastery=p_mastery,
        )

    async def update(self, state: ReplayState, outcome: bool, event_context: EvalEvent) -> ReplayState:
        """Update BKT state with ground-truth outcome."""
        # Get concept_id with fallback
        concept_id, _ = await get_concept_id_with_fallback(
            self.db, event_context.question_id, event_context.theme_id
        )

        # Get or create skill state
        stmt = select(BKTUserSkillState).where(
            BKTUserSkillState.user_id == state.user_id,
            BKTUserSkillState.concept_id == concept_id,
        )
        result = await self.db.execute(stmt)
        skill_state = result.scalar_one_or_none()

        # Get skill params
        stmt = select(BKTSkillParams).where(
            BKTSkillParams.concept_id == concept_id,
            BKTSkillParams.is_active == True,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        skill_params = result.scalar_one_or_none()

        if skill_params:
            p_S = float(skill_params.p_S)
            p_G = float(skill_params.p_G)
        else:
            from app.learning_engine.config import BKT_DEFAULT_G, BKT_DEFAULT_S

            p_S = BKT_DEFAULT_S.value
            p_G = BKT_DEFAULT_G.value

        # Update mastery
        if skill_state:
            p_mastery_prior = float(skill_state.p_mastery)
        else:
            from app.learning_engine.config import BKT_DEFAULT_L0

            p_mastery_prior = BKT_DEFAULT_L0.value

        p_mastery_posterior = posterior_given_obs(p_mastery_prior, outcome, p_S, p_G)

        # Update state (would persist to DB in real implementation)
        if "bkt_states" not in state.algo_state:
            state.algo_state["bkt_states"] = {}
        state.algo_state["bkt_states"][str(concept_id)] = p_mastery_posterior

        return state

    def init_state(self, user_id: UUID) -> ReplayState:
        """Initialize BKT state for a new user."""
        return ReplayState(user_id=user_id, algo_state={"bkt_states": {}})
