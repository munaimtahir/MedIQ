"""FSRS suite implementation for evaluation harness."""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.eval.replay import EvalSuite, ReplayPrediction, ReplayState
from app.learning_engine.eval.dataset import EvalEvent
from app.learning_engine.srs.fsrs_adapter import get_default_parameters
from app.models.srs import SRSConceptState, SRSUserParams

logger = logging.getLogger(__name__)


class FSRSEvalSuite(EvalSuite):
    """FSRS suite for evaluation replay."""

    def __init__(self, db: AsyncSession):
        """Initialize FSRS suite with database session."""
        self.db = db

    async def predict(self, state: ReplayState, event_context: EvalEvent) -> ReplayPrediction:
        """Compute FSRS predictions before state update."""
        # Get user params (for personalized weights if available)
        user_params = await self.db.get(SRSUserParams, state.user_id)

        if user_params and user_params.weights_json:
            weights = user_params.weights_json
            desired_retention = float(user_params.desired_retention)
        else:
            defaults = get_default_parameters()
            weights = defaults["weights"]
            desired_retention = defaults["desired_retention"]

        # Get concept state
        # For FSRS, we need concept_id - use question's concept_id or fallback
        from app.learning_engine.tag_quality import get_concept_id_with_fallback

        concept_id, _ = await get_concept_id_with_fallback(
            self.db, event_context.question_id, event_context.theme_id
        )

        stmt = select(SRSConceptState).where(
            SRSConceptState.user_id == state.user_id,
            SRSConceptState.concept_id == concept_id,
        )
        result = await self.db.execute(stmt)
        concept_state = result.scalar_one_or_none()

        if not concept_state or not concept_state.due_at:
            # No state yet or not due
            p_correct = None
            p_retrievability = None
        else:
            # Compute retrievability
            from fsrs import Scheduler, Card
            from datetime import datetime

            scheduler = Scheduler(parameters=weights, desired_retention=desired_retention)

            card = Card()
            card.stability = concept_state.stability
            card.difficulty = concept_state.difficulty
            card.last_review = concept_state.last_reviewed_at or datetime.utcnow()
            card.due = concept_state.due_at

            # Get retrievability at review time
            review_time = event_context.timestamp or datetime.utcnow()
            p_retrievability = scheduler.get_retrievability(card, review_time)

            # Predict correctness from retrievability
            # FSRS doesn't directly predict correctness, but retrievability correlates
            # For evaluation, we can use retrievability as a proxy
            p_correct = p_retrievability

        return ReplayPrediction(
            event_id=getattr(event_context, "event_id", None),
            p_correct=p_correct,
            p_retrievability=p_retrievability,
        )

    async def update(self, state: ReplayState, outcome: bool, event_context: EvalEvent) -> ReplayState:
        """Update FSRS state with ground-truth outcome."""
        # Get user params
        user_params = await self.db.get(SRSUserParams, state.user_id)

        if user_params and user_params.weights_json:
            weights = user_params.weights_json
            desired_retention = float(user_params.desired_retention)
        else:
            defaults = get_default_parameters()
            weights = defaults["weights"]
            desired_retention = defaults["desired_retention"]

        # Get concept_id
        from app.learning_engine.tag_quality import get_concept_id_with_fallback

        concept_id, _ = await get_concept_id_with_fallback(
            self.db, event_context.question_id, event_context.theme_id
        )

        # Get concept state
        stmt = select(SRSConceptState).where(
            SRSConceptState.user_id == state.user_id,
            SRSConceptState.concept_id == concept_id,
        )
        result = await self.db.execute(stmt)
        concept_state = result.scalar_one_or_none()

        # Convert outcome to FSRS rating (simplified)
        # In real implementation, would use telemetry to determine rating
        rating = 3 if outcome else 1  # Good if correct, Again if wrong

        # Compute delta_days
        if concept_state and concept_state.last_reviewed_at:
            delta_days = (event_context.timestamp - concept_state.last_reviewed_at).total_seconds() / 86400
        else:
            delta_days = 0.0

        # Update FSRS state
        from app.learning_engine.srs.fsrs_adapter import compute_next_state_and_due

        current_stability = concept_state.stability if concept_state else None
        current_difficulty = concept_state.difficulty if concept_state else None

        new_stability, new_difficulty, due_at, retrievability = compute_next_state_and_due(
            current_stability=current_stability,
            current_difficulty=current_difficulty,
            rating=rating,
            delta_days=delta_days,
            weights=weights,
            desired_retention=desired_retention,
            reviewed_at=event_context.timestamp or datetime.utcnow(),
        )

        # Update state (would persist to DB in real implementation)
        if "fsrs_states" not in state.algo_state:
            state.algo_state["fsrs_states"] = {}
        state.algo_state["fsrs_states"][str(concept_id)] = {
            "stability": new_stability,
            "difficulty": new_difficulty,
            "due_at": due_at.isoformat() if due_at else None,
            "retrievability": retrievability,
        }

        return state

    def init_state(self, user_id: UUID) -> ReplayState:
        """Initialize FSRS state for a new user."""
        return ReplayState(user_id=user_id, algo_state={"fsrs_states": {}})
