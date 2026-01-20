"""Feature extraction from telemetry and session data for mistake classification."""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import AttemptEvent, SessionAnswer, SessionQuestion, TestSession

logger = logging.getLogger(__name__)


class AttemptFeatures(BaseModel):
    """Features for a single question attempt."""

    question_id: UUID
    position: int | None
    is_correct: bool
    answered_at: datetime | None

    # Telemetry-derived features (may be None if telemetry missing)
    time_spent_sec: float | None
    change_count: int
    blur_count: int
    mark_for_review_used: bool

    # Session context
    remaining_sec_at_answer: float | None

    # Frozen tags
    year: int | None
    block_id: UUID | None
    theme_id: UUID | None


async def compute_time_spent_by_question(
    db: AsyncSession,
    session_id: UUID,
) -> dict[UUID, float]:
    """
    Compute time spent per question using QUESTION_VIEWED events.

    Time is calculated as the difference between consecutive QUESTION_VIEWED events.
    For the last question, we use session submitted_at - last_view_ts.

    Args:
        db: Database session
        session_id: Session ID

    Returns:
        Dictionary mapping question_id to time_spent_sec (capped at 600s)
    """
    # Get session
    session = await db.get(TestSession, session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        return {}

    # Get QUESTION_VIEWED events ordered by timestamp
    events_stmt = (
        select(AttemptEvent)
        .where(
            AttemptEvent.session_id == session_id,
            AttemptEvent.event_type == "QUESTION_VIEWED",
        )
        .order_by(AttemptEvent.event_ts.asc())
    )
    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    if not events:
        logger.info(f"No QUESTION_VIEWED events for session {session_id}")
        return {}

    time_spent = {}

    # Compute time between consecutive views
    for i, event in enumerate(events):
        question_id = event.payload_json.get("question_id")
        if not question_id:
            continue

        # Parse question_id as UUID
        try:
            question_id = UUID(question_id)
        except (ValueError, TypeError):
            continue

        # Calculate time spent
        if i < len(events) - 1:
            # Time until next question viewed
            next_event = events[i + 1]
            duration = (next_event.event_ts - event.event_ts).total_seconds()
        else:
            # Last question - use session submitted_at
            if session.submitted_at:
                duration = (session.submitted_at - event.event_ts).total_seconds()
            else:
                # Fallback to reasonable default
                duration = 30.0

        # Cap at 600 seconds (10 minutes)
        duration = min(duration, 600.0)

        # Accumulate (in case question viewed multiple times)
        if question_id in time_spent:
            time_spent[question_id] += duration
        else:
            time_spent[question_id] = duration

    # Cap accumulated times at 600s
    for qid in time_spent:
        time_spent[qid] = min(time_spent[qid], 600.0)

    return time_spent


async def compute_change_count(
    db: AsyncSession,
    session_id: UUID,
) -> dict[UUID, int]:
    """
    Count answer changes per question using ANSWER_CHANGED events.

    Args:
        db: Database session
        session_id: Session ID

    Returns:
        Dictionary mapping question_id to change count
    """
    events_stmt = select(AttemptEvent).where(
        AttemptEvent.session_id == session_id,
        AttemptEvent.event_type == "ANSWER_CHANGED",
    )
    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    change_counts = defaultdict(int)

    for event in events:
        question_id = event.payload_json.get("question_id")
        if question_id:
            try:
                question_id = UUID(question_id)
                change_counts[question_id] += 1
            except (ValueError, TypeError):
                continue

    return dict(change_counts)


async def compute_blur_count(
    db: AsyncSession,
    session_id: UUID,
) -> dict[UUID, int]:
    """
    Count blur/tab-away events per question using PAUSE_BLUR events.

    Args:
        db: Database session
        session_id: Session ID

    Returns:
        Dictionary mapping question_id to blur count
    """
    events_stmt = select(AttemptEvent).where(
        AttemptEvent.session_id == session_id,
        AttemptEvent.event_type == "PAUSE_BLUR",
    )
    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    blur_counts = defaultdict(int)

    for event in events:
        # Check if state is "blur"
        state = event.payload_json.get("state")
        if state == "blur":
            question_id = event.payload_json.get("question_id")
            if question_id:
                try:
                    question_id = UUID(question_id)
                    blur_counts[question_id] += 1
                except (ValueError, TypeError):
                    continue

    return dict(blur_counts)


async def compute_mark_for_review(
    db: AsyncSession,
    session_id: UUID,
) -> dict[UUID, bool]:
    """
    Check if questions were marked for review.

    Args:
        db: Database session
        session_id: Session ID

    Returns:
        Dictionary mapping question_id to whether it was marked for review
    """
    events_stmt = select(AttemptEvent).where(
        AttemptEvent.session_id == session_id,
        AttemptEvent.event_type == "MARK_FOR_REVIEW_TOGGLED",
    )
    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    marked = {}

    for event in events:
        is_marked = event.payload_json.get("marked")
        if is_marked:
            question_id = event.payload_json.get("question_id")
            if question_id:
                try:
                    question_id = UUID(question_id)
                    marked[question_id] = True
                except (ValueError, TypeError):
                    continue

    return marked


async def build_features_for_session(
    db: AsyncSession,
    session_id: UUID,
) -> list[AttemptFeatures]:
    """
    Build comprehensive features for all questions in a session.

    Combines data from:
    - session_answers (correctness, answered_at)
    - session_questions (position, frozen tags)
    - attempt_events (time_spent, changes, blur, mark_for_review)
    - test_sessions (timing context)

    Args:
        db: Database session
        session_id: Session ID

    Returns:
        List of AttemptFeatures for each answered question
    """
    # Get session
    session = await db.get(TestSession, session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        return []

    # Get all answers
    answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session_id)
    answers_result = await db.execute(answers_stmt)
    answers = {a.question_id: a for a in answers_result.scalars().all()}

    if not answers:
        logger.info(f"No answers for session {session_id}")
        return []

    # Get session questions (for position and frozen tags)
    questions_stmt = select(SessionQuestion).where(SessionQuestion.session_id == session_id)
    questions_result = await db.execute(questions_stmt)
    session_questions = {sq.question_id: sq for sq in questions_result.scalars().all()}

    # Extract telemetry features (best-effort)
    try:
        time_spent = await compute_time_spent_by_question(db, session_id)
        change_counts = await compute_change_count(db, session_id)
        blur_counts = await compute_blur_count(db, session_id)
        marked = await compute_mark_for_review(db, session_id)
    except Exception as e:
        logger.warning(f"Failed to extract telemetry features for session {session_id}: {e}")
        time_spent = {}
        change_counts = {}
        blur_counts = {}
        marked = {}

    # Build features for each answered question
    features = []

    for question_id, answer in answers.items():
        # Skip if no selected answer
        if answer.selected_index is None:
            continue

        sq = session_questions.get(question_id)

        # Extract frozen tags
        year = None
        block_id = None
        theme_id = None

        if sq:
            if sq.question_version:
                year = sq.question_version.year
                block_id = sq.question_version.block_id
                theme_id = sq.question_version.theme_id
            elif sq.snapshot_json:
                year = sq.snapshot_json.get("year")
                block_id_str = sq.snapshot_json.get("block_id")
                theme_id_str = sq.snapshot_json.get("theme_id")

                # Parse UUIDs
                if block_id_str:
                    try:
                        block_id = UUID(block_id_str)
                    except (ValueError, TypeError):
                        pass

                if theme_id_str:
                    try:
                        theme_id = UUID(theme_id_str)
                    except (ValueError, TypeError):
                        pass

        # Compute remaining time at answer
        remaining_sec = None
        if answer.answered_at and session.expires_at:
            remaining_delta = session.expires_at - answer.answered_at
            remaining_sec = remaining_delta.total_seconds()
        elif answer.answered_at and session.submitted_at:
            remaining_delta = session.submitted_at - answer.answered_at
            remaining_sec = max(remaining_delta.total_seconds(), 0)

        feature = AttemptFeatures(
            question_id=question_id,
            position=sq.order_index if sq else None,
            is_correct=answer.is_correct,
            answered_at=answer.answered_at,
            time_spent_sec=time_spent.get(question_id),
            change_count=change_counts.get(question_id, 0),
            blur_count=blur_counts.get(question_id, 0),
            mark_for_review_used=marked.get(question_id, False),
            remaining_sec_at_answer=remaining_sec,
            year=year,
            block_id=block_id,
            theme_id=theme_id,
        )

        features.append(feature)

    return features
