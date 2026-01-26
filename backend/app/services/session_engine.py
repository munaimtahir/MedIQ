"""Session engine service for test creation, selection, and scoring."""

import hashlib
import random
import uuid
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.question_cms import Question, QuestionStatus
from app.models.session import (
    SessionAnswer,
    SessionQuestion,
    SessionStatus,
    TestSession,
)
from app.schemas.session import SessionCreate
from app.services.session_freeze import freeze_question, get_frozen_content


async def select_questions(
    db: Session,
    filters: SessionCreate,
    user_id: UUID,
    session_seed: str,
) -> list[UUID]:
    """
    Select questions for a session using deterministic seeded ordering.

    Args:
        db: Database session
        filters: Session creation filters
        user_id: User ID (for seed)
        session_seed: Seed string for reproducible shuffle

    Returns:
        List of question IDs (ordered)

    Raises:
        HTTPException: If not enough questions available
    """
    # Build query for eligible PUBLISHED questions
    query = select(Question.id).where(
        Question.status == QuestionStatus.PUBLISHED,
        Question.year_id == filters.year,
    )

    # Filter by blocks
    if filters.blocks:
        from app.models.syllabus import Block

        block_stmt = select(Block.id).where(Block.code.in_(filters.blocks))
        block_result = db.execute(block_stmt)
        block_ids = [row[0] for row in block_result.all()]
        query = query.where(Question.block_id.in_(block_ids))

    # Filter by themes (if provided)
    if filters.themes:
        query = query.where(Question.theme_id.in_(filters.themes))

    # Filter by difficulty (if provided)
    if filters.difficulty:
        query = query.where(Question.difficulty.in_(filters.difficulty))

    # Filter by cognitive level (if provided)
    if filters.cognitive:
        query = query.where(Question.cognitive_level.in_(filters.cognitive))

    # Execute query to get eligible IDs
    result = db.execute(query)
    eligible_ids = [row[0] for row in result.all()]

    # Check if enough questions available
    if len(eligible_ids) < filters.count:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "NOT_ENOUGH_QUESTIONS",
                "message": f"Only {len(eligible_ids)} questions available, but {filters.count} requested",
                "available_count": len(eligible_ids),
                "requested_count": filters.count,
            },
        )

    # Deterministic shuffle using seed
    rng = random.Random(session_seed)
    shuffled_ids = eligible_ids.copy()
    rng.shuffle(shuffled_ids)

    # Take first N questions
    selected_ids = shuffled_ids[: filters.count]

    return selected_ids


async def create_session(
    db: Session,
    user_id: UUID,
    filters: SessionCreate,
) -> TestSession:
    """
    Create a new test session.

    Args:
        db: Database session
        user_id: User ID
        filters: Session creation filters

    Returns:
        Created session

    Raises:
        HTTPException: If invalid filters or not enough questions
    """
    # Create session ID and seed
    session_id = uuid.uuid4()
    started_at = datetime.utcnow()

    # Generate deterministic seed
    seed_parts = [
        str(user_id),
        str(filters.year),
        ",".join(sorted(filters.blocks)),
        ",".join(map(str, sorted(filters.themes or []))),
        filters.mode.value,
        started_at.date().isoformat(),
    ]
    seed_string = ":".join(seed_parts)
    session_seed = hashlib.sha256(seed_string.encode()).hexdigest()

    # Select questions
    question_ids = await select_questions(db, filters, user_id, session_seed)

    # Calculate expiry if duration set
    expires_at = None
    if filters.duration_seconds:
        expires_at = started_at + timedelta(seconds=filters.duration_seconds)

    # Snapshot algorithm runtime config for session continuity (sync DB)
    from app.models.algo_runtime import AlgoBridgeConfig, AlgoRuntimeConfig, AlgoRuntimeProfile

    runtime_row = db.query(AlgoRuntimeConfig).first()
    if not runtime_row:
        runtime_row = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={
                "profile": "V1_PRIMARY",
                "overrides": {},
                "safe_mode": {"freeze_updates": False, "prefer_cache": True},
                "search_engine_mode": "postgres",
            },
        )
        db.add(runtime_row)
        db.commit()
        db.refresh(runtime_row)

    config_json = runtime_row.config_json or {}
    algo_profile_at_start = runtime_row.active_profile.value
    algo_overrides_at_start = (config_json.get("overrides") or {}).copy()

    bridge_row = (
        db.query(AlgoBridgeConfig).filter(AlgoBridgeConfig.policy_version == "ALGO_BRIDGE_SPEC_v1").first()
    )
    algo_policy_version_at_start = bridge_row.policy_version if bridge_row else "ALGO_BRIDGE_SPEC_v1"

    # Snapshot exam mode and freeze-updates at session creation (no mid-session effect)
    from app.system.flags import is_exam_mode, is_freeze_updates

    exam_mode_at_start = is_exam_mode(db)
    freeze_updates_at_start = is_freeze_updates(db)

    # Create session
    session = TestSession(
        id=session_id,
        user_id=user_id,
        mode=filters.mode,
        status=SessionStatus.ACTIVE,
        year=filters.year,
        blocks_json=filters.blocks,
        themes_json=filters.themes,
        total_questions=len(question_ids),
        started_at=started_at,
        duration_seconds=filters.duration_seconds,
        expires_at=expires_at,
        algo_profile_at_start=algo_profile_at_start,
        algo_overrides_at_start=algo_overrides_at_start,
        algo_policy_version_at_start=algo_policy_version_at_start,
        exam_mode_at_start=exam_mode_at_start,
        freeze_updates_at_start=freeze_updates_at_start,
    )
    db.add(session)

    # Create session_questions with frozen content
    for position, question_id in enumerate(question_ids, start=1):
        # Freeze question content
        version_id, snapshot = await freeze_question(db, question_id)

        session_question = SessionQuestion(
            session_id=session_id,
            position=position,
            question_id=question_id,
            question_version_id=version_id,
            snapshot_json=snapshot,
        )
        db.add(session_question)

    # Store runtime snapshot (profile + resolved modules + flags) for no-mid-session change
    from app.runtime_control.snapshot import build_and_store_snapshot

    build_and_store_snapshot(db, session_id)

    db.commit()
    db.refresh(session)

    return session


async def check_and_expire_session(db: Session, session: TestSession) -> TestSession:
    """
    Check if session has expired and auto-submit if needed (lazy expiry).

    Args:
        db: Database session
        session: Session to check

    Returns:
        Updated session (may have new status)
    """
    if session.status != SessionStatus.ACTIVE:
        return session

    if session.expires_at and datetime.utcnow() > session.expires_at:
        # Auto-submit due to expiry
        await submit_session(db, session, auto_expired=True)
        db.refresh(session)

    return session


async def submit_session(
    db: Session,
    session: TestSession,
    auto_expired: bool = False,
) -> TestSession:
    """
    Submit a session and compute final score.
    
    Idempotent: If session is already submitted, returns existing session without error.

    Args:
        db: Database session
        session: Session to submit
        auto_expired: Whether this is an auto-expiry submission

    Returns:
        Updated session with scores
    """
    # Idempotency: If already submitted, return as-is (safe for double-submit)
    if session.status != SessionStatus.ACTIVE:
        # Refresh to get latest state (including scores if already computed)
        db.refresh(session)
        return session

    # Calculate score
    answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session.id)
    answers_result = db.execute(answers_stmt)
    answers = answers_result.scalars().all()

    score_correct = sum(1 for a in answers if a.is_correct is True)
    score_total = session.total_questions
    score_pct = round((score_correct / score_total) * 100, 2) if score_total > 0 else 0.0

    # Update session
    session.status = SessionStatus.EXPIRED if auto_expired else SessionStatus.SUBMITTED
    session.submitted_at = datetime.utcnow()
    session.score_correct = score_correct
    session.score_total = score_total
    session.score_pct = score_pct

    db.commit()
    db.refresh(session)

    return session


async def get_session_progress(db: Session, session_id: UUID) -> dict[str, Any]:
    """
    Get session progress summary.

    Args:
        db: Database session
        session_id: Session ID

    Returns:
        Progress dict with answered_count, marked_for_review_count, current_position
    """
    # Get answers
    answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session_id)
    answers_result = db.execute(answers_stmt)
    answers = answers_result.scalars().all()

    answered_count = sum(1 for a in answers if a.selected_index is not None)
    marked_count = sum(1 for a in answers if a.marked_for_review)

    # Get first unanswered position, else last position
    questions_stmt = (
        select(SessionQuestion)
        .where(SessionQuestion.session_id == session_id)
        .order_by(SessionQuestion.position)
    )
    questions_result = db.execute(questions_stmt)
    questions = questions_result.scalars().all()

    answered_question_ids = {a.question_id for a in answers if a.selected_index is not None}
    current_position = 1

    for q in questions:
        if q.question_id not in answered_question_ids:
            current_position = q.position
            break
    else:
        # All answered, set to last position
        if questions:
            current_position = questions[-1].position

    return {
        "answered_count": answered_count,
        "marked_for_review_count": marked_count,
        "current_position": current_position,
    }


async def process_answer(
    db: Session,
    session: TestSession,
    question_id: UUID,
    selected_index: int | None,
    marked_for_review: bool | None,
) -> SessionAnswer:
    """
    Process an answer submission for a session question.

    Args:
        db: Database session
        session: Test session
        question_id: Question ID
        selected_index: Selected option index (0-4) or None
        marked_for_review: Mark for review flag

    Returns:
        Updated answer

    Raises:
        HTTPException: If session not active or question not in session
    """
    # Check session is active (and not expired)
    session = await check_and_expire_session(db, session)
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    session_id = session.id  # capture before any rollback (session may be expired after)

    # Verify question belongs to session
    session_question_stmt = select(SessionQuestion).where(
        SessionQuestion.session_id == session_id,
        SessionQuestion.question_id == question_id,
    )
    session_question_result = db.execute(session_question_stmt)
    session_question = session_question_result.scalar_one_or_none()

    if not session_question:
        raise HTTPException(status_code=404, detail="Question not in session")

    # Get or create answer
    answer_stmt = select(SessionAnswer).where(
        SessionAnswer.session_id == session_id,
        SessionAnswer.question_id == question_id,
    )
    answer_result = db.execute(answer_stmt)
    answer = answer_result.scalar_one_or_none()

    if not answer:
        answer = SessionAnswer(
            session_id=session_id,
            question_id=question_id,
        )
        db.add(answer)

    # Check if answer changed
    if answer.selected_index is not None and selected_index is not None:
        if answer.selected_index != selected_index:
            answer.changed_count += 1

    # Update answer
    answer.selected_index = selected_index
    if selected_index is not None:
        answer.answered_at = datetime.utcnow()

    if marked_for_review is not None:
        answer.marked_for_review = marked_for_review

    # Compute is_correct using frozen content
    if selected_index is not None:
        frozen_content = await get_frozen_content(
            db,
            question_id,
            session_question.question_version_id,
            session_question.snapshot_json,
        )
        correct_index = frozen_content.get("correct_index")
        answer.is_correct = selected_index == correct_index
    else:
        answer.is_correct = None

    try:
        db.commit()
        db.refresh(answer)
        return answer
    except IntegrityError:
        db.rollback()
        # Duplicate (session_id, question_id): concurrent insert. Refetch and return existing (idempotent).
        db.expire(answer)  # force refetch from DB, not identity map
        refetch = db.execute(
            select(SessionAnswer).where(
                SessionAnswer.session_id == session_id,
                SessionAnswer.question_id == question_id,
            )
        )
        existing = refetch.scalar_one_or_none()
        if existing is None:
            raise
        return existing
