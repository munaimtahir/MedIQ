"""Learning Engine API endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.session import TestSession
from app.models.user import User
from app.schemas.learning import (
    AdaptiveNextRequest,
    AdaptiveNextSummary,
    AlgoInfo,
    DifficultyUpdateRequest,
    DifficultyUpdateSummary,
    LearningResponse,
    MasteryRecomputeRequest,
    MasteryRecomputeSummary,
    MistakesClassifyRequest,
    MistakesClassifySummary,
    RevisionPlanRequest,
    RevisionPlanSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Auth & Ownership Helpers
# ============================================================================


def require_student_or_admin(user: User) -> None:
    """Require user to be STUDENT, ADMIN, or REVIEWER."""
    if user.role not in ["STUDENT", "ADMIN", "REVIEWER"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def assert_user_scope(requested_user_id: UUID | None, current_user: User) -> UUID:
    """
    Enforce user scope for learning operations.
    
    - Students can only operate on themselves
    - Admins/Reviewers can specify any user_id
    
    Returns:
        Effective user_id to use
    """
    # If no user_id specified, use current user
    if requested_user_id is None:
        return current_user.id
    
    # Students cannot specify another user
    if current_user.role == "STUDENT" and requested_user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Students can only access their own data"
        )
    
    # Admin/Reviewer can specify any user
    if current_user.role in ["ADMIN", "REVIEWER"]:
        return requested_user_id
    
    # For current user's own data
    if requested_user_id == current_user.id:
        return current_user.id
    
    raise HTTPException(status_code=403, detail="Insufficient permissions")


async def assert_session_ownership(
    db: AsyncSession,
    session_id: UUID,
    current_user: User,
) -> TestSession:
    """
    Verify session ownership.
    
    - Students can only access their own sessions
    - Admins/Reviewers can access any session
    
    Returns:
        The session if authorized
    """
    session = await db.get(TestSession, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Admin/Reviewer can access any session
    if current_user.role in ["ADMIN", "REVIEWER"]:
        return session
    
    # Students can only access their own sessions
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this session"
        )
    
    return session


# ============================================================================
# Task 111: POST /v1/learning/mastery/recompute
# ============================================================================


@router.post("/mastery/recompute", response_model=LearningResponse)
async def recompute_mastery(
    request: MasteryRecomputeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Recompute Mastery v0 for a user.
    
    - Students can only recompute for themselves
    - Admins/Reviewers can specify any user_id
    - dry_run=true computes counts only without DB writes
    """
    require_student_or_admin(current_user)
    
    # Enforce user scope
    effective_user_id = assert_user_scope(request.user_id, current_user)
    
    # Call mastery service
    from app.learning_engine.mastery.service import recompute_mastery_v0_for_user
    
    result = await recompute_mastery_v0_for_user(
        db,
        user_id=effective_user_id,
        theme_ids=None,  # Recompute all themes
        dry_run=request.dry_run,
    )
    
    # Get algo info from result
    from app.learning_engine.constants import AlgoKey
    from app.learning_engine.registry import resolve_active
    
    version, params_obj = await resolve_active(db, AlgoKey.MASTERY.value)
    
    if not version or not params_obj:
        raise HTTPException(
            status_code=500,
            detail="Mastery algorithm not configured"
        )
    
    # Build response
    summary = MasteryRecomputeSummary(
        themes_processed=result.get("themes_computed", 0),
        records_upserted=result.get("records_upserted", 0),
        dry_run=request.dry_run,
    )
    
    return LearningResponse(
        ok=True,
        run_id=UUID(result["run_id"]),
        algo=AlgoInfo(key="mastery", version=version.version),
        params_id=params_obj.id,
        summary=summary.model_dump(),
    )


# ============================================================================
# Task 112: POST /v1/learning/revision/plan
# ============================================================================


@router.post("/revision/plan", response_model=LearningResponse)
async def generate_revision_plan(
    request: RevisionPlanRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Generate revision_queue entries for a user.
    
    - Students can only plan for themselves
    - Admins/Reviewers can specify any user_id
    - Horizon comes from algo params (not configurable via API)
    """
    require_student_or_admin(current_user)
    
    # Enforce user scope
    effective_user_id = assert_user_scope(request.user_id, current_user)
    
    # Call revision service
    from app.learning_engine.revision.service import generate_revision_queue_v0
    
    result = await generate_revision_queue_v0(
        db,
        user_id=effective_user_id,
        year=request.year,
        block_id=request.block_id,
        trigger="api",
    )
    
    # Get algo info
    from app.learning_engine.constants import AlgoKey
    from app.learning_engine.registry import resolve_active
    
    version, params_obj = await resolve_active(db, AlgoKey.REVISION.value)
    
    if not version or not params_obj:
        raise HTTPException(
            status_code=500,
            detail="Revision algorithm not configured"
        )
    
    # Build response
    summary = RevisionPlanSummary(
        generated=result.get("generated", 0),
        due_today=result.get("due_today", 0),
    )
    
    return LearningResponse(
        ok=True,
        run_id=UUID(result["run_id"]),
        algo=AlgoInfo(key="revision", version=version.version),
        params_id=params_obj.id,
        summary=summary.model_dump(),
    )


# ============================================================================
# Task 113: POST /v1/learning/adaptive/next
# ============================================================================


@router.post("/adaptive/next", response_model=LearningResponse)
async def adaptive_next_questions(
    request: AdaptiveNextRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Select next best questions using Adaptive v0.
    
    - Students can only select for themselves
    - Admins/Reviewers can specify any user_id
    - Does NOT create a session (returns question_ids only)
    - Deterministic output for same inputs
    """
    require_student_or_admin(current_user)
    
    # Enforce user scope
    effective_user_id = assert_user_scope(request.user_id, current_user)
    
    # Call adaptive service
    from app.learning_engine.adaptive.service import adaptive_select_v0
    
    result = await adaptive_select_v0(
        db,
        user_id=effective_user_id,
        year=request.year,
        block_ids=request.block_ids,
        theme_ids=request.theme_ids,
        count=request.count,
        mode=request.mode,
        trigger=f"api_{request.source}",
    )
    
    # Get algo info
    from app.learning_engine.constants import AlgoKey
    from app.learning_engine.registry import resolve_active
    
    version, params_obj = await resolve_active(db, AlgoKey.ADAPTIVE.value)
    
    if not version or not params_obj:
        raise HTTPException(
            status_code=500,
            detail="Adaptive algorithm not configured"
        )
    
    # Compute difficulty distribution (from question_ids)
    # For now, simple placeholder - could query question_difficulty table
    question_ids = result.get("question_ids", [])
    
    # Build response
    summary = AdaptiveNextSummary(
        count=len(question_ids),
        themes_used=[],  # Could extract from selection metadata
        difficulty_distribution={
            "easy": 0,
            "medium": len(question_ids),
            "hard": 0,
        },
        question_ids=question_ids,
    )
    
    return LearningResponse(
        ok=True,
        run_id=UUID(result["run_id"]),
        algo=AlgoInfo(key="adaptive", version=version.version),
        params_id=params_obj.id,
        summary=summary.model_dump(),
    )


# ============================================================================
# Task 114: POST /v1/learning/difficulty/update
# ============================================================================


@router.post("/difficulty/update", response_model=LearningResponse)
async def update_difficulty(
    request: DifficultyUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Update question difficulty ratings for a submitted session.
    
    - Students can only update for their own sessions
    - Admins/Reviewers can update any session
    - Idempotent (safe to call multiple times)
    """
    require_student_or_admin(current_user)
    
    # Verify session ownership
    await assert_session_ownership(db, request.session_id, current_user)
    
    # Call difficulty service
    from app.learning_engine.difficulty.service import update_question_difficulty_v0_for_session
    
    result = await update_question_difficulty_v0_for_session(
        db,
        session_id=request.session_id,
        trigger="api",
    )
    
    # Handle errors from service
    if "error" in result:
        raise HTTPException(
            status_code=500,
            detail=f"Difficulty update failed: {result['error']}"
        )
    
    # Get algo info
    from app.learning_engine.constants import AlgoKey
    from app.learning_engine.registry import resolve_active
    
    version, params_obj = await resolve_active(db, AlgoKey.DIFFICULTY.value)
    
    if not version or not params_obj:
        raise HTTPException(
            status_code=500,
            detail="Difficulty algorithm not configured"
        )
    
    # Build response
    summary = DifficultyUpdateSummary(
        questions_updated=result.get("questions_updated", 0),
        avg_delta=result.get("avg_delta", 0.0),
    )
    
    return LearningResponse(
        ok=True,
        run_id=UUID(result["run_id"]),
        algo=AlgoInfo(key="difficulty", version=version.version),
        params_id=params_obj.id,
        summary=summary.model_dump(),
    )


# ============================================================================
# Task 115: POST /v1/learning/mistakes/classify
# ============================================================================


@router.post("/mistakes/classify", response_model=LearningResponse)
async def classify_mistakes(
    request: MistakesClassifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Classify mistakes for a submitted session.
    
    - Students can only classify for their own sessions
    - Admins/Reviewers can classify any session
    - Idempotent (safe to call multiple times)
    """
    require_student_or_admin(current_user)
    
    # Verify session ownership
    await assert_session_ownership(db, request.session_id, current_user)
    
    # Call mistakes service
    from app.learning_engine.mistakes.service import classify_mistakes_v0_for_session
    
    result = await classify_mistakes_v0_for_session(
        db,
        session_id=request.session_id,
        trigger="api",
    )
    
    # Handle errors from service
    if "error" in result:
        raise HTTPException(
            status_code=500,
            detail=f"Mistake classification failed: {result['error']}"
        )
    
    # Get algo info
    from app.learning_engine.constants import AlgoKey
    from app.learning_engine.registry import resolve_active
    
    version, params_obj = await resolve_active(db, AlgoKey.MISTAKES.value)
    
    if not version or not params_obj:
        raise HTTPException(
            status_code=500,
            detail="Mistakes algorithm not configured"
        )
    
    # Build response
    summary = MistakesClassifySummary(
        total_wrong=result.get("total_wrong", 0),
        classified=result.get("classified", 0),
        counts_by_type=result.get("counts_by_type", {}),
    )
    
    return LearningResponse(
        ok=True,
        run_id=UUID(result["run_id"]),
        algo=AlgoInfo(key="mistakes", version=version.version),
        params_id=params_obj.id,
        summary=summary.model_dump(),
    )
