"""
BKT Service Layer - Manages mastery state updates and persistence.

Handles:
- Fetching active BKT parameters (concept-specific or global default)
- Creating/updating user skill states
- Persisting mastery updates
- Creating historical snapshots
"""

import logging
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.bkt import BKTSkillParams, BKTUserSkillState, MasterySnapshot
from app.models.learning import AlgoVersion, AlgoParams
from app.learning_engine.bkt.core import update_mastery, clamp_probability
from app.learning_engine.constants import AlgoKey

logger = logging.getLogger(__name__)

# Default BKT parameters (fallback when no concept-specific params exist)
DEFAULT_BKT_PARAMS = {
    "p_L0": 0.1,
    "p_T": 0.1,
    "p_S": 0.1,
    "p_G": 0.25,
}


class BKTParams:
    """Container for BKT parameters."""
    
    def __init__(
        self,
        p_L0: float,
        p_T: float,
        p_S: float,
        p_G: float,
        concept_id: Optional[UUID] = None,
        algo_version_id: Optional[UUID] = None,
        is_default: bool = False
    ):
        self.p_L0 = p_L0
        self.p_T = p_T
        self.p_S = p_S
        self.p_G = p_G
        self.concept_id = concept_id
        self.algo_version_id = algo_version_id
        self.is_default = is_default
    
    def to_dict(self) -> dict:
        return {
            "p_L0": self.p_L0,
            "p_T": self.p_T,
            "p_S": self.p_S,
            "p_G": self.p_G,
            "concept_id": str(self.concept_id) if self.concept_id else None,
            "algo_version_id": str(self.algo_version_id) if self.algo_version_id else None,
            "is_default": self.is_default,
        }


async def get_active_params(db: AsyncSession, concept_id: UUID) -> BKTParams:
    """
    Get active BKT parameters for a concept.
    
    Falls back to global default if no concept-specific parameters exist.
    
    Args:
        db: Database session
        concept_id: Concept ID
        
    Returns:
        BKTParams instance
    """
    # Try to get concept-specific parameters
    result = await db.execute(
        select(BKTSkillParams)
        .where(
            and_(
                BKTSkillParams.concept_id == concept_id,
                BKTSkillParams.is_active == True
            )
        )
        .order_by(BKTSkillParams.fitted_at.desc())
        .limit(1)
    )
    
    skill_params = result.scalar_one_or_none()
    
    if skill_params:
        logger.debug(f"Using concept-specific BKT params for concept {concept_id}")
        return BKTParams(
            p_L0=skill_params.p_L0,
            p_T=skill_params.p_T,
            p_S=skill_params.p_S,
            p_G=skill_params.p_G,
            concept_id=concept_id,
            algo_version_id=skill_params.algo_version_id,
            is_default=False
        )
    
    # Fall back to global default parameters
    logger.debug(f"Using default BKT params for concept {concept_id}")
    
    # Get BKT algo version
    result = await db.execute(
        select(AlgoVersion)
        .where(
            and_(
                AlgoVersion.algo_key == AlgoKey.BKT.value,
                AlgoVersion.status == "ACTIVE"
            )
        )
        .limit(1)
    )
    
    algo_version = result.scalar_one_or_none()
    
    if algo_version:
        # Get default params from algo_params
        result = await db.execute(
            select(AlgoParams)
            .where(
                and_(
                    AlgoParams.algo_version_id == algo_version.id,
                    AlgoParams.is_active == True
                )
            )
            .limit(1)
        )
        
        algo_params = result.scalar_one_or_none()
        
        if algo_params and algo_params.params_json:
            params_json = algo_params.params_json
            return BKTParams(
                p_L0=params_json.get("default_L0", DEFAULT_BKT_PARAMS["p_L0"]),
                p_T=params_json.get("default_T", DEFAULT_BKT_PARAMS["p_T"]),
                p_S=params_json.get("default_S", DEFAULT_BKT_PARAMS["p_S"]),
                p_G=params_json.get("default_G", DEFAULT_BKT_PARAMS["p_G"]),
                concept_id=concept_id,
                algo_version_id=algo_version.id,
                is_default=True
            )
    
    # Ultimate fallback
    return BKTParams(
        p_L0=DEFAULT_BKT_PARAMS["p_L0"],
        p_T=DEFAULT_BKT_PARAMS["p_T"],
        p_S=DEFAULT_BKT_PARAMS["p_S"],
        p_G=DEFAULT_BKT_PARAMS["p_G"],
        concept_id=concept_id,
        is_default=True
    )


async def get_or_create_user_state(
    db: AsyncSession,
    user_id: UUID,
    concept_id: UUID,
    default_from_L0: Optional[float] = None
) -> BKTUserSkillState:
    """
    Get or create user skill state for a concept.
    
    If state doesn't exist, creates it with p_mastery = L0 (prior).
    
    Args:
        db: Database session
        user_id: User ID
        concept_id: Concept ID
        default_from_L0: Optional L0 value for initialization
        
    Returns:
        BKTUserSkillState instance
    """
    # Try to get existing state
    result = await db.execute(
        select(BKTUserSkillState)
        .where(
            and_(
                BKTUserSkillState.user_id == user_id,
                BKTUserSkillState.concept_id == concept_id
            )
        )
    )
    
    state = result.scalar_one_or_none()
    
    if state:
        return state
    
    # Create new state with L0 as initial mastery
    if default_from_L0 is None:
        params = await get_active_params(db, concept_id)
        default_from_L0 = params.p_L0
    
    state = BKTUserSkillState(
        user_id=user_id,
        concept_id=concept_id,
        p_mastery=default_from_L0,
        n_attempts=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    
    db.add(state)
    await db.flush()  # Flush to get the state persisted but don't commit yet
    
    logger.info(f"Created new BKT state for user {user_id}, concept {concept_id} with L0={default_from_L0:.3f}")
    
    return state


async def update_from_attempt(
    db: AsyncSession,
    user_id: UUID,
    question_id: UUID,
    concept_id: UUID,
    correct: bool,
    create_snapshot: bool = False,
    meta: Optional[dict] = None
) -> dict:
    """
    Update user mastery from a single attempt.
    
    Steps:
    1. Get active BKT parameters for concept
    2. Get or create user skill state
    3. Apply BKT update
    4. Persist updated state
    5. Optionally create historical snapshot
    
    Args:
        db: Database session
        user_id: User ID
        question_id: Question ID
        concept_id: Primary concept ID for this question
        correct: Whether the answer was correct
        create_snapshot: Whether to create a historical snapshot
        meta: Optional metadata (e.g., response time, confidence)
        
    Returns:
        Dict with:
            - p_mastery_prior: Mastery before update
            - p_mastery_new: Mastery after update
            - mastery_change: Difference
            - n_attempts: Total attempts
            - params_used: BKT parameters used
            - metadata: BKT computation metadata
    """
    # Get BKT parameters
    params = await get_active_params(db, concept_id)
    
    # Get or create user state
    state = await get_or_create_user_state(db, user_id, concept_id, params.p_L0)
    
    # Store prior mastery
    p_mastery_prior = state.p_mastery
    
    # Apply BKT update
    p_mastery_new, bkt_metadata = update_mastery(
        p_L_current=state.p_mastery,
        correct=correct,
        p_T=params.p_T,
        p_S=params.p_S,
        p_G=params.p_G
    )
    
    # Update state
    state.p_mastery = p_mastery_new
    state.n_attempts += 1
    state.last_attempt_at = datetime.now(UTC)
    state.last_seen_question_id = question_id
    state.algo_version_id = params.algo_version_id
    state.updated_at = datetime.now(UTC)
    
    # Commit the state update
    await db.flush()
    
    logger.info(
        f"Updated BKT mastery for user {user_id}, concept {concept_id}: "
        f"{p_mastery_prior:.3f} -> {p_mastery_new:.3f} (correct={correct})"
    )
    
    # Optionally create snapshot
    if create_snapshot:
        snapshot = MasterySnapshot(
            user_id=user_id,
            concept_id=concept_id,
            p_mastery=p_mastery_new,
            n_attempts=state.n_attempts,
            algo_version_id=params.algo_version_id,
            created_at=datetime.now(UTC)
        )
        db.add(snapshot)
        await db.flush()
    
    # Return summary
    return {
        "user_id": str(user_id),
        "concept_id": str(concept_id),
        "question_id": str(question_id),
        "correct": correct,
        "p_mastery_prior": p_mastery_prior,
        "p_mastery_new": p_mastery_new,
        "mastery_change": p_mastery_new - p_mastery_prior,
        "n_attempts": state.n_attempts,
        "params_used": params.to_dict(),
        "bkt_metadata": bkt_metadata,
        "snapshot_created": create_snapshot,
    }


async def get_user_mastery(
    db: AsyncSession,
    user_id: UUID,
    concept_ids: Optional[list[UUID]] = None
) -> list[dict]:
    """
    Get current mastery states for a user.
    
    Args:
        db: Database session
        user_id: User ID
        concept_ids: Optional list of concept IDs to filter
        
    Returns:
        List of mastery state dicts
    """
    query = select(BKTUserSkillState).where(BKTUserSkillState.user_id == user_id)
    
    if concept_ids:
        query = query.where(BKTUserSkillState.concept_id.in_(concept_ids))
    
    result = await db.execute(query.order_by(BKTUserSkillState.p_mastery.desc()))
    states = result.scalars().all()
    
    return [
        {
            "concept_id": str(state.concept_id),
            "p_mastery": state.p_mastery,
            "n_attempts": state.n_attempts,
            "last_attempt_at": state.last_attempt_at.isoformat() if state.last_attempt_at else None,
            "is_mastered": state.p_mastery >= 0.95,  # Default threshold
            "updated_at": state.updated_at.isoformat(),
        }
        for state in states
    ]


async def batch_update_from_attempts(
    db: AsyncSession,
    user_id: UUID,
    attempts: list[dict]
) -> list[dict]:
    """
    Batch update mastery from multiple attempts.
    
    Useful for recomputing mastery from historical data.
    
    Args:
        db: Database session
        user_id: User ID
        attempts: List of attempt dicts with keys:
            - question_id
            - concept_id
            - correct
            - timestamp (optional)
            
    Returns:
        List of update result dicts
    """
    results = []
    
    # Sort attempts by timestamp if available
    sorted_attempts = sorted(
        attempts,
        key=lambda x: x.get("timestamp", datetime.now(UTC))
    )
    
    for attempt in sorted_attempts:
        result = await update_from_attempt(
            db=db,
            user_id=user_id,
            question_id=attempt["question_id"],
            concept_id=attempt["concept_id"],
            correct=attempt["correct"],
            create_snapshot=False,  # Don't create snapshots in batch mode
            meta=attempt.get("meta")
        )
        results.append(result)
    
    return results
