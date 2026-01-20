"""Session endpoints for test engine."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.session import SessionAnswer, SessionQuestion, SessionStatus, TestSession
from app.models.user import User
from app.schemas.session import (
    AnswerOut,
    AnswerSubmit,
    AnswerSubmitResponse,
    CurrentQuestionOut,
    ReviewAnswer,
    ReviewItem,
    ReviewQuestionContent,
    SessionCreate,
    SessionCreateResponse,
    SessionOut,
    SessionProgress,
    SessionQuestionSummary,
    SessionReviewOut,
    SessionStateOut,
    SessionStateWithCurrentOut,
    SessionSubmitResponse,
)
from app.services.session_engine import (
    check_and_expire_session,
    create_session,
    get_session_progress,
    process_answer,
    submit_session,
)
from app.services.session_freeze import get_frozen_content
from app.services.telemetry import log_event

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================


async def get_user_session(
    db: AsyncSession,
    session_id: UUID,
    user: User,
) -> TestSession:
    """Get session and verify ownership."""
    stmt = (
        select(TestSession)
        .where(TestSession.id == session_id)
        .options(
            selectinload(TestSession.questions),
            selectinload(TestSession.answers),
        )
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    return session


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/sessions", response_model=SessionCreateResponse)
async def create_test_session(
    filters: SessionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Create a new test session.

    Selects questions based on filters and creates a session.
    Questions are frozen at creation time for review consistency.
    """
    # Create session
    session = await create_session(db, current_user.id, filters)

    # Log event
    await log_event(
        db,
        session.id,
        current_user.id,
        "SESSION_CREATED",
        {
            "mode": filters.mode.value,
            "year": filters.year,
            "blocks": filters.blocks,
            "themes": filters.themes,
            "count": filters.count,
            "duration_seconds": filters.duration_seconds,
        },
    )
    await db.commit()

    # Get progress
    progress_data = await get_session_progress(db, session.id)

    return SessionCreateResponse(
        session_id=session.id,
        status=session.status,
        mode=session.mode,
        total_questions=session.total_questions,
        started_at=session.started_at,
        expires_at=session.expires_at,
        progress=SessionProgress(**progress_data),
    )


@router.get("/sessions/{session_id}", response_model=SessionStateWithCurrentOut)
async def get_session_state(
    session_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get current session state with progress and question list.

    Includes current question content (without answer/explanation).
    Applies lazy expiry if session has expired.
    """
    session = await get_user_session(db, session_id, current_user)

    # Check and apply lazy expiry
    session = await check_and_expire_session(db, session)

    # Get progress
    progress_data = await get_session_progress(db, session.id)

    # Get questions summary
    questions_stmt = (
        select(SessionQuestion)
        .where(SessionQuestion.session_id == session.id)
        .order_by(SessionQuestion.position)
    )
    questions_result = await db.execute(questions_stmt)
    questions = questions_result.scalars().all()

    # Get answers
    answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session.id)
    answers_result = await db.execute(answers_stmt)
    answers = answers_result.scalars().all()
    answers_map = {a.question_id: a for a in answers}

    question_summaries = []
    for q in questions:
        answer = answers_map.get(q.question_id)
        question_summaries.append(
            SessionQuestionSummary(
                position=q.position,
                question_id=q.question_id,
                has_answer=answer is not None and answer.selected_index is not None,
                marked_for_review=answer.marked_for_review if answer else False,
            )
        )

    # Get current question content (without answer/explanation)
    current_question = None
    current_pos = progress_data["current_position"]
    current_session_q = next((q for q in questions if q.position == current_pos), None)

    if current_session_q:
        frozen = await get_frozen_content(
            db,
            current_session_q.question_id,
            current_session_q.question_version_id,
            current_session_q.snapshot_json,
        )
        current_question = CurrentQuestionOut(
            question_id=current_session_q.question_id,
            position=current_session_q.position,
            stem=frozen["stem"],
            option_a=frozen["option_a"],
            option_b=frozen["option_b"],
            option_c=frozen["option_c"],
            option_d=frozen["option_d"],
            option_e=frozen["option_e"],
            year_id=frozen.get("year_id"),
            block_id=frozen.get("block_id"),
            theme_id=frozen.get("theme_id"),
        )

    return SessionStateWithCurrentOut(
        session=SessionOut.from_orm(session),
        progress=SessionProgress(**progress_data),
        questions=question_summaries,
        current_question=current_question,
    )


@router.post("/sessions/{session_id}/answer", response_model=AnswerSubmitResponse)
async def submit_answer(
    session_id: UUID,
    answer_data: AnswerSubmit,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Submit an answer for a question in the session.

    Updates answer and computes correctness using frozen question content.
    Tracks answer changes and marked for review status.
    """
    session = await get_user_session(db, session_id, current_user)

    # Process answer
    answer = await process_answer(
        db,
        session,
        answer_data.question_id,
        answer_data.selected_index,
        answer_data.marked_for_review,
    )

    # Log event
    await log_event(
        db,
        session.id,
        current_user.id,
        "ANSWER_SUBMITTED",
        {
            "question_id": str(answer_data.question_id),
            "selected_index": answer_data.selected_index,
            "changed_count": answer.changed_count,
            "marked_for_review": answer.marked_for_review,
        },
    )
    await db.commit()

    # Get updated progress
    progress_data = await get_session_progress(db, session.id)

    return AnswerSubmitResponse(
        answer=AnswerOut.from_orm(answer),
        progress=SessionProgress(**progress_data),
    )


@router.post("/sessions/{session_id}/submit", response_model=SessionSubmitResponse)
async def submit_test_session(
    session_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Submit the session and finalize scoring.

    Computes final score (unanswered = incorrect, no negative marking).
    Locks the session from further answers.
    """
    session = await get_user_session(db, session_id, current_user)

    # Submit session
    session = await submit_session(db, session)

    # Log event
    await log_event(
        db,
        session.id,
        current_user.id,
        "SESSION_SUBMITTED",
        {
            "score_correct": session.score_correct,
            "score_total": session.score_total,
            "score_pct": float(session.score_pct) if session.score_pct else 0.0,
        },
    )
    await db.commit()
    
    # Best-effort learning algorithm updates (do not block submission)
    # These run after commit, so submission is already persisted
    
    # 1. Update question difficulty ratings (ELO-lite)
    try:
        from app.learning_engine.difficulty.service import update_question_difficulty_v0_for_session
        await update_question_difficulty_v0_for_session(db, session_id, trigger="submit")
    except Exception as e:
        # Log but don't fail
        import logging
        logging.getLogger(__name__).warning(f"Difficulty update failed for session {session_id}: {e}")
    
    # 2. Classify mistakes (rule-based)
    try:
        from app.learning_engine.mistakes.service import classify_mistakes_v0_for_session
        await classify_mistakes_v0_for_session(db, session_id, trigger="submit")
    except Exception as e:
        # Log but don't fail
        import logging
        logging.getLogger(__name__).warning(f"Mistake classification failed for session {session_id}: {e}")

    return SessionSubmitResponse(
        session_id=session.id,
        status=session.status,
        score_correct=session.score_correct,
        score_total=session.score_total,
        score_pct=float(session.score_pct),
        submitted_at=session.submitted_at,
    )


@router.get("/sessions/{session_id}/review", response_model=SessionReviewOut)
async def review_session(
    session_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Review a submitted/expired session.

    Returns all questions with frozen content (stem, options, correct answer, explanation)
    and user's answers with correctness.
    """
    session = await get_user_session(db, session_id, current_user)

    # Check session is submitted or expired
    if session.status not in (SessionStatus.SUBMITTED, SessionStatus.EXPIRED):
        raise HTTPException(status_code=400, detail="Session must be submitted to review")

    # Get questions (ordered by position)
    questions_stmt = (
        select(SessionQuestion)
        .where(SessionQuestion.session_id == session.id)
        .order_by(SessionQuestion.position)
    )
    questions_result = await db.execute(questions_stmt)
    questions = questions_result.scalars().all()

    # Get answers
    answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session.id)
    answers_result = await db.execute(answers_stmt)
    answers = answers_result.scalars().all()
    answers_map = {a.question_id: a for a in answers}

    # Build review items
    items = []
    for q in questions:
        # Get frozen content
        frozen = await get_frozen_content(
            db,
            q.question_id,
            q.question_version_id,
            q.snapshot_json,
        )

        question_content = ReviewQuestionContent(
            question_id=q.question_id,
            position=q.position,
            stem=frozen["stem"],
            option_a=frozen["option_a"],
            option_b=frozen["option_b"],
            option_c=frozen["option_c"],
            option_d=frozen["option_d"],
            option_e=frozen["option_e"],
            correct_index=frozen["correct_index"],
            explanation_md=frozen.get("explanation_md"),
            year_id=frozen.get("year_id"),
            block_id=frozen.get("block_id"),
            theme_id=frozen.get("theme_id"),
            source_book=frozen.get("source_book"),
            source_page=frozen.get("source_page"),
        )

        # Get user answer
        answer = answers_map.get(q.question_id)
        review_answer = ReviewAnswer(
            question_id=q.question_id,
            selected_index=answer.selected_index if answer else None,
            is_correct=answer.is_correct if answer else None,
            marked_for_review=answer.marked_for_review if answer else False,
            answered_at=answer.answered_at if answer else None,
            changed_count=answer.changed_count if answer else 0,
        )

        items.append(ReviewItem(question=question_content, answer=review_answer))

    # Log event
    await log_event(
        db,
        session.id,
        current_user.id,
        "SESSION_REVIEW_VIEWED",
        None,
    )
    await db.commit()

    return SessionReviewOut(
        session=SessionOut.from_orm(session),
        items=items,
    )
