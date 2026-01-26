"""Session endpoints for test engine."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.runtime_control import require_mutations_allowed
from app.security.rate_limit import create_user_rate_limit_dep
from app.models.session import (
    AttemptEvent,
    SessionAnswer,
    SessionQuestion,
    SessionStatus,
    TestSession,
)
from app.models.user import User
from app.schemas.session import (
    AnswerOut,
    AnswerSubmit,
    AnswerSubmitResponse,
    AnswerSubmitThin,
    AnswerSubmitThinResponse,
    CurrentQuestionOut,
    PrefetchQuestionsOut,
    QuestionThinOut,
    QuestionWithAnswerStateOut,
    ReviewAnswer,
    ReviewItem,
    ReviewQuestionContent,
    SessionCreate,
    SessionCreateResponse,
    SessionOut,
    SessionProgress,
    SessionQuestionSummary,
    SessionReviewOut,
    SessionStateThinOut,
    SessionStateWithCurrentOut,
    SessionSubmitResponse,
    SessionSubmitThinResponse,
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


def get_user_session(
    db: Session,
    session_id: UUID,
    user: User,
) -> TestSession:
    """Get session and verify ownership."""
    session = (
        db.query(TestSession)
        .filter(TestSession.id == session_id)
        .options(
            selectinload(TestSession.questions),
            selectinload(TestSession.answers),
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    return session


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "",
    response_model=SessionCreateResponse,
    dependencies=[Depends(create_user_rate_limit_dep("sessions.create", fail_open=True))],
)
async def create_test_session(
    filters: SessionCreate,
    db: Annotated[Session, Depends(get_db)],
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
    db.commit()

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


@router.get("/{session_id}", response_model=SessionStateWithCurrentOut)
async def get_session_state(
    session_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get current session state with progress and question list.

    Includes current question content (without answer/explanation).
    Applies lazy expiry if session has expired.
    """
    session = get_user_session(db, session_id, current_user)

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
    questions_result = db.execute(questions_stmt)
    questions = questions_result.scalars().all()

    # Get answers
    answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session.id)
    answers_result = db.execute(answers_stmt)
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


@router.post(
    "/{session_id}/answer",
    response_model=AnswerSubmitResponse,
    dependencies=[Depends(require_mutations_allowed("session_answer"))],
)
async def submit_answer(
    session_id: UUID,
    answer_data: AnswerSubmit,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Submit an answer for a question in the session.

    Updates answer and computes correctness using frozen question content.
    Tracks answer changes and marked for review status.
    """
    session = get_user_session(db, session_id, current_user)

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
    db.commit()

    # Get updated progress
    progress_data = await get_session_progress(db, session.id)

    return AnswerSubmitResponse(
        answer=AnswerOut.from_orm(answer),
        progress=SessionProgress(**progress_data),
    )


@router.post(
    "/{session_id}/submit",
    response_model=SessionSubmitResponse,
    dependencies=[
        Depends(create_user_rate_limit_dep("sessions.submit", fail_open=True)),
        Depends(require_mutations_allowed("session_submit")),
    ],
)
async def submit_test_session(
    session_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Submit the session and finalize scoring.

    Computes final score (unanswered = incorrect, no negative marking).
    Locks the session from further answers.
    
    Idempotent: Safe to call multiple times (returns existing result if already submitted).
    """
    session = get_user_session(db, session_id, current_user)

    # Store status before submission to detect if it was already submitted
    was_already_submitted = session.status != SessionStatus.ACTIVE
    
    # Submit session (idempotent - safe for double-submit)
    session = await submit_session(db, session)
    
    # Only log event if session was just submitted (not already submitted)
    if not was_already_submitted:
        # Log event only on first submission
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
        db.commit()

    # Best-effort learning algorithm updates (do not block submission).
    # These run after commit, so submission is already persisted
    # Use session snapshot for algorithm version (ensures continuity)
    #
    # NOTE: In this codebase, the DB session is synchronous (psycopg2). The learning-engine
    # runtime helpers are async and expect AsyncSession. Skip these updates unless we are
    # running with an actual AsyncSession.
    session_profile = session.algo_profile_at_start
    session_overrides = session.algo_overrides_at_start or {}
    try:
        from sqlalchemy.ext.asyncio import AsyncSession as SAAsyncSession
    except Exception:  # pragma: no cover
        SAAsyncSession = None  # type: ignore[assignment]

    if SAAsyncSession is not None and isinstance(db, SAAsyncSession):
        # 1. Update question difficulty ratings (routed based on session snapshot)
        try:
            from app.learning_engine.runtime import get_session_algo_config

            algo_config = await get_session_algo_config(db, session_profile, session_overrides)
            difficulty_version = algo_config.get("difficulty", "v1")

            if difficulty_version == "v0":
                from app.learning_engine.difficulty.service import update_question_difficulty_v0_for_session

                await update_question_difficulty_v0_for_session(db, session_id, trigger="submit")
            else:
                # v1 difficulty (ELO) - already handles updates per attempt
                pass
        except Exception as e:
            # Log but don't fail
            import logging

            logging.getLogger(__name__).warning(
                f"Difficulty update failed for session {session_id}: {e}"
            )

        # 2. Classify mistakes (routed based on session snapshot)
        try:
            from app.learning_engine.runtime import get_session_algo_config

            algo_config = await get_session_algo_config(db, session_profile, session_overrides)
            mistakes_version = algo_config.get("mistakes", "v1")

            if mistakes_version == "v0":
                from app.learning_engine.mistakes.service import classify_mistakes_v0_for_session

                await classify_mistakes_v0_for_session(db, session_id, trigger="submit")
            else:
                from app.learning_engine.mistakes_v1.service import classify_mistakes_v1_for_session

                await classify_mistakes_v1_for_session(db, session_id, trigger="submit")
        except Exception as e:
            # Log but don't fail
            import logging

            logging.getLogger(__name__).warning(
                f"Mistake classification failed for session {session_id}: {e}"
            )

        # 3. Update BKT mastery (Bayesian Knowledge Tracing)
        # NOTE: BKT integration requires concept_id extraction from session questions.
        # Concept mapping is not yet implemented, so BKT updates are skipped.
        # To implement: extract concept_id from question metadata, call update_bkt_from_attempt.
        try:
            from datetime import datetime

            from app.learning_engine.bkt.service import update_bkt_from_attempt

            # Get all answers for this session
            answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session_id)
            answers_result = await db.execute(answers_stmt)
            answers = answers_result.scalars().all()

            # Get session questions to extract concept_ids
            questions_stmt = select(SessionQuestion).where(SessionQuestion.session_id == session_id)
            questions_result = await db.execute(questions_stmt)
            questions = questions_result.scalars().all()
            questions_map = {q.question_id: q for q in questions}

            # Update BKT for each answered question
            for answer in answers:
                if answer.is_correct is None:
                    continue  # Skip unanswered

                # Get concept_id from snapshot_json
                session_question = questions_map.get(answer.question_id)
                if not session_question or not session_question.snapshot_json:
                    continue

                concept_id_str = session_question.snapshot_json.get("concept_id")
                if not concept_id_str:
                    continue  # No concept mapping

                try:
                    from uuid import UUID as UUIDType

                    concept_id = UUIDType(concept_id_str)

                    # Update BKT mastery
                    await update_bkt_from_attempt(
                        db,
                        user_id=current_user.id,
                        question_id=answer.question_id,
                        concept_id=concept_id,
                        correct=answer.is_correct,
                        current_time=answer.answered_at or datetime.now(),
                        snapshot_mastery=False,  # Don't create snapshots on every submit
                    )
                except (ValueError, KeyError):
                    # Invalid concept_id or BKT update failed for this question
                    pass

            # Commit BKT updates
            await db.commit()

        except Exception as e:
            # Log but don't fail
            import logging

            logging.getLogger(__name__).warning(
                f"BKT mastery update failed for session {session_id}: {e}"
            )

        # 4. Update SRS (Spaced Repetition System) - FSRS-based forgetting model
        # Note: Similar to BKT, requires concept_id extraction from session questions
        try:
            from datetime import datetime

            from app.learning_engine.mistakes.features import (
                compute_change_count,
                compute_time_spent_by_question,
            )
            from app.learning_engine.srs.service import update_from_attempt

            # Get all answers and questions (reuse if already loaded)
            if not answers:
                answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session_id)
                answers_result = await db.execute(answers_stmt)
                answers = answers_result.scalars().all()

            if not questions:
                questions_stmt = select(SessionQuestion).where(SessionQuestion.session_id == session_id)
                questions_result = await db.execute(questions_stmt)
                questions = questions_result.scalars().all()
                questions_map = {q.question_id: q for q in questions}

            # Get telemetry for rating computation
            events_stmt = (
                select(AttemptEvent)
                .where(AttemptEvent.session_id == session_id)
                .order_by(AttemptEvent.event_ts)
            )
            events_result = await db.execute(events_stmt)
            events = events_result.scalars().all()

            # Compute telemetry features per question
            time_by_question = compute_time_spent_by_question(events)
            changes_by_question = compute_change_count(events)

            # Update SRS for each answered question
            for answer in answers:
                if answer.is_correct is None:
                    continue  # Skip unanswered

                # Get concept_id(s) from snapshot_json
                session_question = questions_map.get(answer.question_id)
                if not session_question or not session_question.snapshot_json:
                    continue

                # Extract concept_ids (can be single or list)
                snapshot = session_question.snapshot_json
                concept_ids = []

                # Try single concept_id first
                concept_id_str = snapshot.get("concept_id")
                if concept_id_str:
                    try:
                        from uuid import UUID as UUIDType

                        concept_ids.append(UUIDType(concept_id_str))
                    except (ValueError, TypeError):
                        pass

                # Try concept_ids list
                concept_ids_list = snapshot.get("concept_ids", [])
                if concept_ids_list:
                    for cid_str in concept_ids_list:
                        try:
                            from uuid import UUID as UUIDType

                            concept_ids.append(UUIDType(cid_str))
                        except (ValueError, TypeError):
                            pass

                if not concept_ids:
                    continue  # No concept mapping

                # Build telemetry dict
                telemetry = {
                    "time_spent_ms": time_by_question.get(answer.question_id),
                    "change_count": changes_by_question.get(answer.question_id, 0),
                    "marked_for_review": answer.marked_for_review,
                }

                # Update SRS
                try:
                    await update_from_attempt(
                        db,
                        user_id=current_user.id,
                        concept_ids=concept_ids,
                        correct=answer.is_correct,
                        occurred_at=answer.answered_at or datetime.now(),
                        telemetry=telemetry,
                        raw_attempt_id=answer.id,
                        session_id=session_id,
                    )
                except Exception as e:
                    # Log but continue with other questions
                    import logging

                    logging.getLogger(__name__).warning(
                        f"SRS update failed for question {answer.question_id}: {e}"
                    )

            # Commit SRS updates
            await db.commit()

        except Exception as e:
            # Log but don't fail
            import logging

            logging.getLogger(__name__).warning(f"SRS update failed for session {session_id}: {e}")

    session_profile = session.algo_profile_at_start
    session_overrides = session.algo_overrides_at_start or {}

    # 1. Update question difficulty ratings (routed based on session snapshot)
    try:
        from app.learning_engine.runtime import get_session_algo_config

        algo_config = await get_session_algo_config(db, session_profile, session_overrides)
        difficulty_version = algo_config.get("difficulty", "v1")

        if difficulty_version == "v0":
            from app.learning_engine.difficulty.service import update_question_difficulty_v0_for_session

            await update_question_difficulty_v0_for_session(db, session_id, trigger="submit")
        else:
            # v1 difficulty (ELO) - already handles updates per attempt
            pass
    except Exception as e:
        # Log but don't fail
        import logging

        logging.getLogger(__name__).warning(
            f"Difficulty update failed for session {session_id}: {e}"
        )

    # 2. Classify mistakes (routed based on session snapshot)
    try:
        from app.learning_engine.runtime import get_session_algo_config

        algo_config = await get_session_algo_config(db, session_profile, session_overrides)
        mistakes_version = algo_config.get("mistakes", "v1")

        if mistakes_version == "v0":
            from app.learning_engine.mistakes.service import classify_mistakes_v0_for_session

            await classify_mistakes_v0_for_session(db, session_id, trigger="submit")
        else:
            from app.learning_engine.mistakes_v1.service import classify_mistakes_v1_for_session

            await classify_mistakes_v1_for_session(db, session_id, trigger="submit")
    except Exception as e:
        # Log but don't fail
        import logging

        logging.getLogger(__name__).warning(
            f"Mistake classification failed for session {session_id}: {e}"
        )

    # 3. Update BKT mastery (Bayesian Knowledge Tracing)
    # NOTE: BKT integration requires concept_id extraction from session questions.
    # Concept mapping is not yet implemented, so BKT updates are skipped.
    # To implement: extract concept_id from question metadata, call update_bkt_from_attempt.
    try:
        from datetime import datetime

        from app.learning_engine.bkt.service import update_bkt_from_attempt

        # Get all answers for this session
        answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session_id)
        answers_result = db.execute(answers_stmt)
        answers = answers_result.scalars().all()

        # Get session questions to extract concept_ids
        questions_stmt = select(SessionQuestion).where(SessionQuestion.session_id == session_id)
        questions_result = db.execute(questions_stmt)
        questions = questions_result.scalars().all()
        questions_map = {q.question_id: q for q in questions}

        # Update BKT for each answered question
        for answer in answers:
            if answer.is_correct is None:
                continue  # Skip unanswered

            # Get concept_id from snapshot_json
            session_question = questions_map.get(answer.question_id)
            if not session_question or not session_question.snapshot_json:
                continue

            concept_id_str = session_question.snapshot_json.get("concept_id")
            if not concept_id_str:
                continue  # No concept mapping

            try:
                from uuid import UUID as UUIDType

                concept_id = UUIDType(concept_id_str)

                # Update BKT mastery
                await update_bkt_from_attempt(
                    db,
                    user_id=current_user.id,
                    question_id=answer.question_id,
                    concept_id=concept_id,
                    correct=answer.is_correct,
                    current_time=answer.answered_at or datetime.now(),
                    snapshot_mastery=False,  # Don't create snapshots on every submit
                )
            except (ValueError, KeyError):
                # Invalid concept_id or BKT update failed for this question
                pass

        # Commit BKT updates
        db.commit()

    except Exception as e:
        # Log but don't fail
        import logging

        logging.getLogger(__name__).warning(
            f"BKT mastery update failed for session {session_id}: {e}"
        )

    # 4. Update SRS (Spaced Repetition System) - FSRS-based forgetting model
    # Note: Similar to BKT, requires concept_id extraction from session questions
    try:
        from datetime import datetime

        from app.learning_engine.mistakes.features import (
            compute_change_count,
            compute_time_spent_by_question,
        )
        from app.learning_engine.srs.service import update_from_attempt

        # Get all answers and questions (reuse if already loaded)
        if not answers:
            answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session_id)
            answers_result = db.execute(answers_stmt)
            answers = answers_result.scalars().all()

        if not questions:
            questions_stmt = select(SessionQuestion).where(SessionQuestion.session_id == session_id)
            questions_result = db.execute(questions_stmt)
            questions = questions_result.scalars().all()
            questions_map = {q.question_id: q for q in questions}

        # Get telemetry for rating computation
        events_stmt = (
            select(AttemptEvent)
            .where(AttemptEvent.session_id == session_id)
            .order_by(AttemptEvent.event_ts)
        )
        events_result = db.execute(events_stmt)
        events = events_result.scalars().all()

        # Compute telemetry features per question
        time_by_question = compute_time_spent_by_question(events)
        changes_by_question = compute_change_count(events)

        # Update SRS for each answered question
        for answer in answers:
            if answer.is_correct is None:
                continue  # Skip unanswered

            # Get concept_id(s) from snapshot_json
            session_question = questions_map.get(answer.question_id)
            if not session_question or not session_question.snapshot_json:
                continue

            # Extract concept_ids (can be single or list)
            snapshot = session_question.snapshot_json
            concept_ids = []

            # Try single concept_id first
            concept_id_str = snapshot.get("concept_id")
            if concept_id_str:
                try:
                    from uuid import UUID as UUIDType

                    concept_ids.append(UUIDType(concept_id_str))
                except (ValueError, TypeError):
                    pass

            # Try concept_ids list
            concept_ids_list = snapshot.get("concept_ids", [])
            if concept_ids_list:
                for cid_str in concept_ids_list:
                    try:
                        from uuid import UUID as UUIDType

                        concept_ids.append(UUIDType(cid_str))
                    except (ValueError, TypeError):
                        pass

            if not concept_ids:
                continue  # No concept mapping

            # Build telemetry dict
            telemetry = {
                "time_spent_ms": time_by_question.get(answer.question_id),
                "change_count": changes_by_question.get(answer.question_id, 0),
                "marked_for_review": answer.marked_for_review,
            }

            # Update SRS
            try:
                await update_from_attempt(
                    db,
                    user_id=current_user.id,
                    concept_ids=concept_ids,
                    correct=answer.is_correct,
                    occurred_at=answer.answered_at or datetime.now(),
                    telemetry=telemetry,
                    raw_attempt_id=answer.id,
                    session_id=session_id,
                )
            except Exception as e:
                # Log but continue with other questions
                import logging

                logging.getLogger(__name__).warning(
                    f"SRS update failed for question {answer.question_id}: {e}"
                )

        # Commit SRS updates
        db.commit()

    except Exception as e:
        # Log but don't fail
        import logging

        logging.getLogger(__name__).warning(f"SRS update failed for session {session_id}: {e}")

    return SessionSubmitResponse(
        session_id=session.id,
        status=session.status,
        score_correct=session.score_correct,
        score_total=session.score_total,
        score_pct=float(session.score_pct),
        submitted_at=session.submitted_at,
    )


# ============================================================================
# Thin Endpoints (Optimized for Player UX)
# ============================================================================


@router.get("/{session_id}/state", response_model=SessionStateThinOut)
async def get_session_state_thin(
    session_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get minimal session state (metadata only, no question content).

    Optimized for frequent polling/updates during test play.
    """
    session = get_user_session(db, session_id, current_user)

    # Check and apply lazy expiry
    session = await check_and_expire_session(db, session)

    # Get progress
    progress_data = await get_session_progress(db, session.id)

    # Build algo snapshot (optional)
    algo_snapshot = None
    if session.algo_profile_at_start:
        algo_snapshot = {
            "profile": session.algo_profile_at_start,
            "overrides": session.algo_overrides_at_start or {},
        }

    return SessionStateThinOut(
        session_id=session.id,
        mode=session.mode,
        status=session.status,
        total_questions=session.total_questions,
        current_index=progress_data["current_position"],
        answered_count=progress_data["answered_count"],
        remaining_count=session.total_questions - progress_data["answered_count"],
        time_limit_seconds=session.duration_seconds,
        started_at=session.started_at,
        server_now=datetime.utcnow(),
        algo_snapshot=algo_snapshot,
    )


@router.get("/{session_id}/question", response_model=QuestionWithAnswerStateOut)
async def get_session_question(
    session_id: UUID,
    index: Annotated[int, Query(ge=1, description="Question index (1-based)")],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get a single question by index (thin payload, no explanation/tags).

    Optimized for prefetching and instant navigation.
    """
    session = get_user_session(db, session_id, current_user)

    # Check and apply lazy expiry
    session = await check_and_expire_session(db, session)

    # Get question by position
    question_stmt = (
        select(SessionQuestion)
        .where(SessionQuestion.session_id == session.id, SessionQuestion.position == index)
        .limit(1)
    )
    question_result = db.execute(question_stmt)
    session_question = question_result.scalar_one_or_none()

    if not session_question:
        raise HTTPException(status_code=404, detail=f"Question at index {index} not found")

    # Get frozen content
    frozen = await get_frozen_content(
        db,
        session_question.question_id,
        session_question.question_version_id,
        session_question.snapshot_json,
    )

    # Get answer state
    answer_stmt = select(SessionAnswer).where(
        SessionAnswer.session_id == session.id, SessionAnswer.question_id == session_question.question_id
    )
    answer_result = db.execute(answer_stmt)
    answer = answer_result.scalar_one_or_none()

    # Build options list
    options = [
        frozen.get("option_a", ""),
        frozen.get("option_b", ""),
        frozen.get("option_c", ""),
        frozen.get("option_d", ""),
        frozen.get("option_e", ""),
    ]

    # Build media list (if any in snapshot)
    media = frozen.get("media", [])
    if not isinstance(media, list):
        media = []

    return QuestionWithAnswerStateOut(
        session_id=session.id,
        index=index,
        question=QuestionThinOut(
            question_id=session_question.question_id,
            stem=frozen["stem"],
            options=options,
            media=media,
        ),
        answer_state={
            "selected_index": answer.selected_index if answer else None,
            "marked_for_review": answer.marked_for_review if answer else False,
        },
    )


@router.get("/{session_id}/questions/prefetch", response_model=PrefetchQuestionsOut)
async def prefetch_questions(
    session_id: UUID,
    from_index: Annotated[int, Query(ge=1, alias="from", description="Start index (1-based)")],
    count: Annotated[int, Query(ge=1, le=5, description="Number of questions to prefetch (max 5)")],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Prefetch multiple questions (for instant navigation).

    Hard cap: count <= 5 to prevent abuse.
    """
    session = get_user_session(db, session_id, current_user)

    # Check and apply lazy expiry
    session = await check_and_expire_session(db, session)

    # Get questions in range
    question_stmt = (
        select(SessionQuestion)
        .where(
            SessionQuestion.session_id == session.id,
            SessionQuestion.position >= from_index,
            SessionQuestion.position < from_index + count,
        )
        .order_by(SessionQuestion.position)
    )
    question_result = db.execute(question_stmt)
    session_questions = question_result.scalars().all()

    if not session_questions:
        return PrefetchQuestionsOut(items=[])

    # Get all answers for these questions
    question_ids = [sq.question_id for sq in session_questions]
    answers_stmt = select(SessionAnswer).where(
        SessionAnswer.session_id == session.id, SessionAnswer.question_id.in_(question_ids)
    )
    answers_result = db.execute(answers_stmt)
    answers = answers_result.scalars().all()
    answers_map = {a.question_id: a for a in answers}

    # Build items
    items = []
    for sq in session_questions:
        # Get frozen content
        frozen = await get_frozen_content(
            db, sq.question_id, sq.question_version_id, sq.snapshot_json
        )

        # Build options
        options = [
            frozen.get("option_a", ""),
            frozen.get("option_b", ""),
            frozen.get("option_c", ""),
            frozen.get("option_d", ""),
            frozen.get("option_e", ""),
        ]

        # Build media
        media = frozen.get("media", [])
        if not isinstance(media, list):
            media = []

        # Get answer state
        answer = answers_map.get(sq.question_id)

        items.append(
            QuestionWithAnswerStateOut(
                session_id=session.id,
                index=sq.position,
                question=QuestionThinOut(
                    question_id=sq.question_id,
                    stem=frozen["stem"],
                    options=options,
                    media=media,
                ),
                answer_state={
                    "selected_index": answer.selected_index if answer else None,
                    "marked_for_review": answer.marked_for_review if answer else False,
                },
            )
        )

    return PrefetchQuestionsOut(items=items)


@router.post(
    "/{session_id}/answer-thin",
    response_model=AnswerSubmitThinResponse,
    dependencies=[Depends(require_mutations_allowed("session_answer_thin"))],
)
async def submit_answer_thin(
    session_id: UUID,
    answer_data: AnswerSubmitThin,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Submit an answer (thin endpoint, idempotent with client_event_id).

    Optimized for player: returns minimal response, supports idempotency.
    """
    session = get_user_session(db, session_id, current_user)

    # Check idempotency (if client_event_id provided, check if already processed)
    # For MVP, we'll just process normally. Full idempotency would require
    # storing client_event_id in a separate table or in answer metadata.
    # For now, we rely on the unique constraint (session_id, question_id).

    # Process answer
    answer = await process_answer(
        db,
        session,
        answer_data.question_id,
        answer_data.selected_index,
        answer_data.marked_for_review,
    )

    # Log event (include client_event_id if provided)
    event_payload = {
        "question_id": str(answer_data.question_id),
        "index": answer_data.index,
        "selected_index": answer_data.selected_index,
        "changed_count": answer.changed_count,
        "marked_for_review": answer.marked_for_review,
    }
    if answer_data.client_event_id:
        event_payload["client_event_id"] = str(answer_data.client_event_id)

    await log_event(
        db,
        session.id,
        current_user.id,
        "ANSWER_SUBMITTED",
        event_payload,
    )
    db.commit()

    return AnswerSubmitThinResponse(
        ok=True,
        server_now=datetime.utcnow(),
        answer_state={
            "selected_index": answer.selected_index,
            "marked_for_review": answer.marked_for_review,
        },
    )


@router.post(
    "/{session_id}/submit-thin",
    response_model=SessionSubmitThinResponse,
    dependencies=[Depends(require_mutations_allowed("session_submit_thin"))],
)
async def submit_test_session_thin(
    session_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Submit the session (thin endpoint).

    Returns minimal response with review URL.
    """
    session = get_user_session(db, session_id, current_user)

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
    db.commit()

    return SessionSubmitThinResponse(
        ok=True,
        submitted_at=session.submitted_at or datetime.utcnow(),
        review_url=f"/v1/sessions/{session.id}/review",
    )


@router.get("/{session_id}/review", response_model=SessionReviewOut)
async def review_session(
    session_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Review a submitted/expired session.

    Returns all questions with frozen content (stem, options, correct answer, explanation)
    and user's answers with correctness.
    """
    session = get_user_session(db, session_id, current_user)

    # Check session is submitted or expired
    if session.status not in (SessionStatus.SUBMITTED, SessionStatus.EXPIRED):
        raise HTTPException(status_code=400, detail="Session must be submitted to review")

    # Get questions (ordered by position)
    questions_stmt = (
        select(SessionQuestion)
        .where(SessionQuestion.session_id == session.id)
        .order_by(SessionQuestion.position)
    )
    questions_result = db.execute(questions_stmt)
    questions = questions_result.scalars().all()

    # Get answers
    answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session.id)
    answers_result = db.execute(answers_stmt)
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
    db.commit()

    return SessionReviewOut(
        session=SessionOut.from_orm(session),
        items=items,
    )
