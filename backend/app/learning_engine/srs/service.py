"""
SRS service layer - orchestrates FSRS updates from MCQ attempts.

Main responsibilities:
- Load/create user FSRS parameters
- Update concept states from attempts  
- Log reviews for training
- Maintain revision queue (materialized view)
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.srs import SRSConceptState, SRSReviewLog, SRSUserParams
from app.models.learning_revision import RevisionQueue
from app.learning_engine.srs.fsrs_adapter import (
    compute_next_state_and_due,
    get_default_parameters,
)
from app.learning_engine.srs.rating_mapper import (
    map_attempt_to_rating,
    validate_telemetry,
)

logger = logging.getLogger(__name__)


async def get_user_params(db: AsyncSession, user_id: UUID) -> SRSUserParams:
    """
    Get or create user FSRS parameters.
    
    Returns defaults if user has no personalized weights yet.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        SRSUserParams instance
    """
    result = await db.execute(
        select(SRSUserParams).where(SRSUserParams.user_id == user_id)
    )
    params = result.scalar_one_or_none()
    
    if params:
        return params
    
    # Create new user params with defaults
    params = SRSUserParams(
        user_id=user_id,
        fsrs_version="fsrs-6",
        weights_json=None,  # Will use global defaults
        desired_retention=0.90,
        n_review_logs=0,
    )
    db.add(params)
    await db.flush()
    
    logger.info(f"Created default SRS params for user {user_id}")
    return params


async def update_from_attempt(
    db: AsyncSession,
    user_id: UUID,
    concept_ids: List[UUID],
    correct: bool,
    occurred_at: datetime,
    telemetry: Optional[dict] = None,
    raw_attempt_id: Optional[UUID] = None,
    session_id: Optional[UUID] = None,
) -> List[dict]:
    """
    Update SRS state from an MCQ attempt.
    
    For each concept:
    1. Load current state (or create new)
    2. Compute delta_days since last review
    3. Map attempt to FSRS rating
    4. Compute new S/D/due using FSRS
    5. Append to review_log
    6. Upsert concept_state
    7. Update revision_queue (materialized)
    
    Args:
        db: Database session
        user_id: User ID
        concept_ids: List of concept IDs tested by this question
        correct: Whether answer was correct
        occurred_at: Timestamp of attempt
        telemetry: Optional dict with time_spent_ms, change_count, marked_for_review
        raw_attempt_id: Optional source session_answer.id
        session_id: Optional source test_session.id
        
    Returns:
        List of dicts with updated state for each concept
    """
    if not concept_ids:
        logger.warning("update_from_attempt called with no concept_ids")
        return []
    
    # Get user params (weights, desired_retention)
    user_params = await get_user_params(db, user_id)
    
    # Use personalized weights if available, else defaults
    weights = user_params.weights_json or get_default_parameters()["weights"]
    desired_retention = user_params.desired_retention
    
    # Extract and validate telemetry
    time_spent_ms = None
    change_count = None
    marked_for_review = False
    
    if telemetry:
        time_spent_ms = telemetry.get("time_spent_ms")
        change_count = telemetry.get("change_count")
        marked_for_review = telemetry.get("marked_for_review", False)
        
        # Validate telemetry
        time_spent_ms, change_count, warnings = validate_telemetry(
            time_spent_ms, change_count
        )
        if warnings:
            logger.warning(f"Telemetry validation warnings: {warnings}")
    
    # Map MCQ attempt to FSRS rating
    rating = map_attempt_to_rating(
        correct=correct,
        time_spent_ms=time_spent_ms,
        change_count=change_count,
        marked_for_review=marked_for_review,
    )
    
    updated_states = []
    
    for concept_id in concept_ids:
        try:
            # Load current state
            result = await db.execute(
                select(SRSConceptState).where(
                    and_(
                        SRSConceptState.user_id == user_id,
                        SRSConceptState.concept_id == concept_id
                    )
                )
            )
            state = result.scalar_one_or_none()
            
            # Compute delta_days
            if state and state.last_reviewed_at:
                delta_days = (occurred_at - state.last_reviewed_at).total_seconds() / 86400
                delta_days = max(0.0, delta_days)  # Ensure non-negative
            else:
                delta_days = 0.0  # First review
            
            # Compute new state using FSRS
            current_stability = state.stability if state else None
            current_difficulty = state.difficulty if state else None
            
            new_stability, new_difficulty, new_due_at, retrievability = compute_next_state_and_due(
                current_stability=current_stability,
                current_difficulty=current_difficulty,
                rating=rating,
                delta_days=delta_days,
                weights=weights,
                desired_retention=desired_retention,
                reviewed_at=occurred_at,
            )
            
            # Upsert concept state
            upsert_stmt = (
                pg_insert(SRSConceptState)
                .values(
                    user_id=user_id,
                    concept_id=concept_id,
                    stability=new_stability,
                    difficulty=new_difficulty,
                    last_reviewed_at=occurred_at,
                    due_at=new_due_at,
                    last_retrievability=retrievability,
                    updated_at=datetime.now(UTC),
                )
                .on_conflict_do_update(
                    index_elements=["user_id", "concept_id"],
                    set_={
                        "stability": new_stability,
                        "difficulty": new_difficulty,
                        "last_reviewed_at": occurred_at,
                        "due_at": new_due_at,
                        "last_retrievability": retrievability,
                        "updated_at": datetime.now(UTC),
                    }
                )
            )
            await db.execute(upsert_stmt)
            
            # Append review log
            review_log = SRSReviewLog(
                user_id=user_id,
                concept_id=concept_id,
                reviewed_at=occurred_at,
                rating=rating,
                correct=correct,
                delta_days=delta_days,
                time_spent_ms=time_spent_ms,
                change_count=change_count,
                predicted_retrievability=retrievability,
                raw_attempt_id=raw_attempt_id,
                session_id=session_id,
            )
            db.add(review_log)
            
            # Update materialized revision queue if it exists
            # (Synchronize with revision_queue table used by UI)
            try:
                await _sync_revision_queue(
                    db,
                    user_id=user_id,
                    concept_id=concept_id,
                    due_at=new_due_at,
                    retrievability=retrievability,
                )
            except Exception as e:
                # Don't fail the whole update if revision_queue sync fails
                logger.warning(f"Failed to sync revision_queue for concept {concept_id}: {e}")
            
            updated_states.append({
                "concept_id": concept_id,
                "stability": new_stability,
                "difficulty": new_difficulty,
                "due_at": new_due_at,
                "retrievability": retrievability,
                "rating": rating,
            })
            
        except Exception as e:
            logger.error(f"Failed to update SRS state for concept {concept_id}: {e}", exc_info=True)
            # Continue with other concepts
    
    # Increment user's review log count
    user_params.n_review_logs += len(updated_states)
    user_params.updated_at = datetime.now(UTC)
    db.add(user_params)
    
    await db.flush()
    
    logger.info(f"Updated SRS for user {user_id}: {len(updated_states)} concepts, rating={rating}")
    
    return updated_states


async def _sync_revision_queue(
    db: AsyncSession,
    user_id: UUID,
    concept_id: UUID,
    due_at: datetime,
    retrievability: float,
) -> None:
    """
    Sync revision_queue table with SRS state (materialized view).
    
    This maintains compatibility with existing revision UI.
    
    Args:
        db: Database session
        user_id: User ID
        concept_id: Concept ID (maps to theme_id in revision_queue)
        due_at: Next review due date
        retrievability: Current retrievability
    """
    # Check if revision_queue exists and has this entry
    # For now, assume concept_id maps to theme_id
    # In production, you'd need proper concept->theme mapping
    
    # This is a best-effort sync - if revision_queue doesn't exist or
    # doesn't have the right schema, we just skip it
    
    # Placeholder implementation - in production, implement proper sync
    # based on your revision_queue schema
    pass


async def get_due_concepts(
    db: AsyncSession,
    user_id: UUID,
    scope: str = "today",
    limit: int = 100,
) -> List[dict]:
    """
    Get concepts due for review.
    
    Args:
        db: Database session
        user_id: User ID
        scope: "today" or "week"
        limit: Max concepts to return
        
    Returns:
        List of dicts with concept info + due date + priority
    """
    now = datetime.now(UTC)
    
    if scope == "today":
        end_date = now
    elif scope == "week":
        end_date = now + timedelta(days=7)
    else:
        raise ValueError(f"Invalid scope: {scope}. Must be 'today' or 'week'.")
    
    # Query due concepts
    query = (
        select(SRSConceptState)
        .where(
            and_(
                SRSConceptState.user_id == user_id,
                SRSConceptState.due_at.isnot(None),
                SRSConceptState.due_at <= end_date
            )
        )
        .order_by(SRSConceptState.due_at)
        .limit(limit)
    )
    
    result = await db.execute(query)
    states = result.scalars().all()
    
    # Convert to output format
    due_concepts = []
    for state in states:
        # Compute priority (lower retrievability = higher priority)
        priority_score = 1.0 - (state.last_retrievability or 0.5)
        
        # Determine if overdue
        is_overdue = state.due_at < now
        days_overdue = (now - state.due_at).total_seconds() / 86400 if is_overdue else 0
        
        # Bucket by day
        if is_overdue:
            bucket = "overdue"
        elif state.due_at.date() == now.date():
            bucket = "today"
        else:
            days_until = (state.due_at - now).days
            if days_until <= 1:
                bucket = "tomorrow"
            elif days_until <= 7:
                bucket = f"day_{days_until}"
            else:
                bucket = "later"
        
        due_concepts.append({
            "concept_id": state.concept_id,
            "due_at": state.due_at,
            "stability": state.stability,
            "difficulty": state.difficulty,
            "retrievability": state.last_retrievability,
            "priority_score": priority_score,
            "is_overdue": is_overdue,
            "days_overdue": days_overdue if is_overdue else None,
            "bucket": bucket,
        })
    
    return due_concepts


async def get_user_stats(
    db: AsyncSession,
    user_id: UUID,
) -> dict:
    """
    Get user's SRS statistics.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Dict with stats: total_concepts, due_today, due_week, etc.
    """
    now = datetime.now(UTC)
    
    # Get user params
    user_params = await get_user_params(db, user_id)
    
    # Count total concepts
    result = await db.execute(
        select(func.count(SRSConceptState.concept_id)).where(
            SRSConceptState.user_id == user_id
        )
    )
    total_concepts = result.scalar() or 0
    
    # Count due today
    result = await db.execute(
        select(func.count(SRSConceptState.concept_id)).where(
            and_(
                SRSConceptState.user_id == user_id,
                SRSConceptState.due_at.isnot(None),
                SRSConceptState.due_at <= now
            )
        )
    )
    due_today = result.scalar() or 0
    
    # Count due this week
    week_end = now + timedelta(days=7)
    result = await db.execute(
        select(func.count(SRSConceptState.concept_id)).where(
            and_(
                SRSConceptState.user_id == user_id,
                SRSConceptState.due_at.isnot(None),
                SRSConceptState.due_at <= week_end
            )
        )
    )
    due_week = result.scalar() or 0
    
    return {
        "total_concepts": total_concepts,
        "due_today": due_today,
        "due_this_week": due_week,
        "total_reviews": user_params.n_review_logs,
        "has_personalized_weights": user_params.weights_json is not None,
        "last_trained_at": user_params.last_trained_at,
    }
