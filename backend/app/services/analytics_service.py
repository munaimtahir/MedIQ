"""Analytics service for computing student performance metrics."""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mistakes import MistakeLog
from app.models.session import AttemptEvent, SessionAnswer, SessionQuestion, SessionStatus, TestSession
from app.models.syllabus import Block, Theme

logger = logging.getLogger(__name__)


def get_block_theme_from_frozen(session_question: SessionQuestion) -> tuple[int | None, int | None]:
    """
    Extract block_id and theme_id from frozen question content.

    Tries question_version first, falls back to snapshot_json.
    """
    # Try version first
    if session_question.question_version:
        return (
            session_question.question_version.block_id,
            session_question.question_version.theme_id,
        )

    # Fallback to snapshot
    if session_question.snapshot_json:
        return (
            session_question.snapshot_json.get("block_id"),
            session_question.snapshot_json.get("theme_id"),
        )

    return None, None


async def get_overview(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    """
    Get student analytics overview.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Dictionary with overview analytics
    """
    # Get all completed sessions for user
    sessions_stmt = select(TestSession).where(
        TestSession.user_id == user_id,
        TestSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.EXPIRED]),
    )
    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()

    if not sessions:
        return _empty_overview()

    session_ids = [s.id for s in sessions]

    # Overall stats
    sessions_completed = len(sessions)

    # Questions from these sessions
    questions_stmt = select(SessionQuestion).where(SessionQuestion.session_id.in_(session_ids))
    questions_result = await db.execute(questions_stmt)
    session_questions = questions_result.scalars().all()

    questions_seen = len(session_questions)

    # Answers
    answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id.in_(session_ids))
    answers_result = await db.execute(answers_stmt)
    answers = answers_result.scalars().all()

    questions_answered = sum(1 for a in answers if a.selected_index is not None)
    correct = sum(1 for a in answers if a.is_correct is True)
    # Accuracy is correct / questions_seen (all questions in session)
    accuracy_pct = round((correct / questions_seen * 100), 2) if questions_seen > 0 else 0.0

    # By block breakdown
    block_stats = {}
    for sq in session_questions:
        block_id, theme_id = get_block_theme_from_frozen(sq)
        if block_id:
            if block_id not in block_stats:
                block_stats[block_id] = {"attempted": 0, "correct": 0}
            block_stats[block_id]["attempted"] += 1

            # Find corresponding answer
            answer = next(
                (
                    a
                    for a in answers
                    if a.question_id == sq.question_id and a.session_id == sq.session_id
                ),
                None,
            )
            if answer and answer.is_correct:
                block_stats[block_id]["correct"] += 1

    # Get block names
    block_ids = list(block_stats.keys())
    blocks_stmt = select(Block).where(Block.id.in_(block_ids))
    blocks_result = await db.execute(blocks_stmt)
    blocks = {b.id: b for b in blocks_result.scalars().all()}

    by_block = [
        {
            "block_id": block_id,
            "block_name": blocks[block_id].name if block_id in blocks else f"Block {block_id}",
            "attempted": stats["attempted"],
            "correct": stats["correct"],
            "accuracy_pct": (
                round((stats["correct"] / stats["attempted"] * 100), 2)
                if stats["attempted"] > 0
                else 0.0
            ),
        }
        for block_id, stats in block_stats.items()
    ]
    by_block.sort(key=lambda x: x["accuracy_pct"])

    # Weakest themes (min 5 attempts)
    theme_stats = {}
    for sq in session_questions:
        block_id, theme_id = get_block_theme_from_frozen(sq)
        if theme_id:
            if theme_id not in theme_stats:
                theme_stats[theme_id] = {"attempted": 0, "correct": 0}
            theme_stats[theme_id]["attempted"] += 1

            answer = next(
                (
                    a
                    for a in answers
                    if a.question_id == sq.question_id and a.session_id == sq.session_id
                ),
                None,
            )
            if answer and answer.is_correct:
                theme_stats[theme_id]["correct"] += 1

    # Get theme names
    theme_ids = [tid for tid, stats in theme_stats.items() if stats["attempted"] >= 5]
    if theme_ids:
        themes_stmt = select(Theme).where(Theme.id.in_(theme_ids))
        themes_result = await db.execute(themes_stmt)
        themes = {t.id: t for t in themes_result.scalars().all()}

        weakest_themes = [
            {
                "theme_id": theme_id,
                "theme_name": themes[theme_id].title if theme_id in themes else f"Theme {theme_id}",
                "attempted": stats["attempted"],
                "correct": stats["correct"],
                "accuracy_pct": (
                    round((stats["correct"] / stats["attempted"] * 100), 2)
                    if stats["attempted"] > 0
                    else 0.0
                ),
            }
            for theme_id, stats in theme_stats.items()
            if stats["attempted"] >= 5
        ]
        weakest_themes.sort(key=lambda x: x["accuracy_pct"])
        weakest_themes = weakest_themes[:10]
    else:
        weakest_themes = []

    # Trend (last 90 days)
    since_date = datetime.utcnow() - timedelta(days=90)
    trend_sessions = [s for s in sessions if s.submitted_at and s.submitted_at >= since_date]

    daily_stats = {}
    for session in trend_sessions:
        if not session.submitted_at:
            continue
        day = session.submitted_at.date()
        if day not in daily_stats:
            daily_stats[day] = {"attempted": 0, "correct": 0}
        daily_stats[day]["attempted"] += session.score_total or 0
        daily_stats[day]["correct"] += session.score_correct or 0

    trend = [
        {
            "date": day,
            "attempted": stats["attempted"],
            "correct": stats["correct"],
            "accuracy_pct": (
                round((stats["correct"] / stats["attempted"] * 100), 2)
                if stats["attempted"] > 0
                else 0.0
            ),
        }
        for day, stats in sorted(daily_stats.items())
    ]

    # Last session
    last_session = max(sessions, key=lambda s: s.submitted_at or datetime.min)
    last_session_summary = (
        {
            "session_id": last_session.id,
            "score_pct": float(last_session.score_pct or 0.0),
            "submitted_at": last_session.submitted_at,
        }
        if last_session
        else None
    )

    # Compute avg_time_sec_per_question from telemetry
    avg_time_sec = await _compute_avg_time_per_question(db, user_id, session_ids)

    return {
        "sessions_completed": sessions_completed,
        "questions_seen": questions_seen,
        "questions_answered": questions_answered,
        "correct": correct,
        "accuracy_pct": accuracy_pct,
        "avg_time_sec_per_question": avg_time_sec,
        "by_block": by_block,
        "weakest_themes": weakest_themes,
        "trend": trend,
        "last_session": last_session_summary,
    }


async def get_block_analytics(
    db: AsyncSession, user_id: UUID, block_id: int
) -> dict[str, Any] | None:
    """
    Get block-specific analytics.

    Args:
        db: Database session
        user_id: User ID
        block_id: Block ID

    Returns:
        Dictionary with block analytics or None if no data
    """
    # Verify block exists
    block_stmt = select(Block).where(Block.id == block_id)
    block_result = await db.execute(block_stmt)
    block = block_result.scalar_one_or_none()

    if not block:
        return None

    # Get completed sessions
    sessions_stmt = select(TestSession).where(
        TestSession.user_id == user_id,
        TestSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.EXPIRED]),
    )
    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()

    if not sessions:
        return _empty_block_analytics(block)

    session_ids = [s.id for s in sessions]

    # Get questions and answers for this block
    questions_stmt = select(SessionQuestion).where(SessionQuestion.session_id.in_(session_ids))
    questions_result = await db.execute(questions_stmt)
    all_questions = questions_result.scalars().all()

    # Filter to this block
    block_questions = [sq for sq in all_questions if get_block_theme_from_frozen(sq)[0] == block_id]

    if not block_questions:
        return _empty_block_analytics(block)

    # Get answers
    question_ids = [sq.question_id for sq in block_questions]
    answers_stmt = select(SessionAnswer).where(
        SessionAnswer.session_id.in_(session_ids),
        SessionAnswer.question_id.in_(question_ids),
    )
    answers_result = await db.execute(answers_stmt)
    answers = answers_result.scalars().all()

    # Compute totals
    attempted = len(block_questions)
    correct = sum(1 for a in answers if a.is_correct is True)
    accuracy_pct = round((correct / attempted * 100), 2) if attempted > 0 else 0.0

    # Theme breakdown
    theme_stats = {}
    for sq in block_questions:
        _, theme_id = get_block_theme_from_frozen(sq)
        if theme_id:
            if theme_id not in theme_stats:
                theme_stats[theme_id] = {"attempted": 0, "correct": 0}
            theme_stats[theme_id]["attempted"] += 1

            answer = next(
                (
                    a
                    for a in answers
                    if a.question_id == sq.question_id and a.session_id == sq.session_id
                ),
                None,
            )
            if answer and answer.is_correct:
                theme_stats[theme_id]["correct"] += 1

    # Get theme names
    theme_ids = list(theme_stats.keys())
    themes_stmt = select(Theme).where(Theme.id.in_(theme_ids))
    themes_result = await db.execute(themes_stmt)
    themes = {t.id: t for t in themes_result.scalars().all()}

    themes_list = [
        {
            "theme_id": theme_id,
            "theme_name": themes[theme_id].title if theme_id in themes else f"Theme {theme_id}",
            "attempted": stats["attempted"],
            "correct": stats["correct"],
            "accuracy_pct": (
                round((stats["correct"] / stats["attempted"] * 100), 2)
                if stats["attempted"] > 0
                else 0.0
            ),
        }
        for theme_id, stats in theme_stats.items()
    ]
    themes_list.sort(key=lambda x: x["accuracy_pct"])

    # Trend (last 90 days)
    trend = _compute_trend_for_items(sessions, block_questions, answers)

    return {
        "block_id": block_id,
        "block_name": block.name,
        "attempted": attempted,
        "correct": correct,
        "accuracy_pct": accuracy_pct,
        "themes": themes_list,
        "trend": trend,
    }


async def get_theme_analytics(
    db: AsyncSession, user_id: UUID, theme_id: int
) -> dict[str, Any] | None:
    """
    Get theme-specific analytics.

    Args:
        db: Database session
        user_id: User ID
        theme_id: Theme ID

    Returns:
        Dictionary with theme analytics or None if no data
    """
    # Verify theme exists
    theme_stmt = select(Theme).where(Theme.id == theme_id)
    theme_result = await db.execute(theme_stmt)
    theme = theme_result.scalar_one_or_none()

    if not theme:
        return None

    # Get block
    block_stmt = select(Block).where(Block.id == theme.block_id)
    block_result = await db.execute(block_stmt)
    block = block_result.scalar_one_or_none()

    # Get completed sessions
    sessions_stmt = select(TestSession).where(
        TestSession.user_id == user_id,
        TestSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.EXPIRED]),
    )
    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()

    if not sessions:
        return _empty_theme_analytics(theme, block)

    session_ids = [s.id for s in sessions]

    # Get questions for this theme
    questions_stmt = select(SessionQuestion).where(SessionQuestion.session_id.in_(session_ids))
    questions_result = await db.execute(questions_stmt)
    all_questions = questions_result.scalars().all()

    theme_questions = [sq for sq in all_questions if get_block_theme_from_frozen(sq)[1] == theme_id]

    if not theme_questions:
        return _empty_theme_analytics(theme, block)

    # Get answers
    question_ids = [sq.question_id for sq in theme_questions]
    answers_stmt = select(SessionAnswer).where(
        SessionAnswer.session_id.in_(session_ids),
        SessionAnswer.question_id.in_(question_ids),
    )
    answers_result = await db.execute(answers_stmt)
    answers = answers_result.scalars().all()

    # Compute totals
    attempted = len(theme_questions)
    correct = sum(1 for a in answers if a.is_correct is True)
    accuracy_pct = round((correct / attempted * 100), 2) if attempted > 0 else 0.0

    # Trend
    trend = _compute_trend_for_items(sessions, theme_questions, answers)

    # Compute common mistakes from mistake_log
    common_mistakes = await _compute_common_mistakes(db, user_id, theme_id)

    return {
        "theme_id": theme_id,
        "theme_name": theme.title,
        "block_id": theme.block_id,
        "block_name": block.name if block else "",
        "attempted": attempted,
        "correct": correct,
        "accuracy_pct": accuracy_pct,
        "trend": trend,
        "common_mistakes": common_mistakes,
    }


def _compute_trend_for_items(sessions, questions, answers) -> list[dict]:
    """Compute daily trend for given questions/answers."""
    since_date = datetime.utcnow() - timedelta(days=90)

    # Build question->session mapping
    question_session_map = {(sq.question_id, sq.session_id): sq for sq in questions}

    daily_stats = {}
    for answer in answers:
        key = (answer.question_id, answer.session_id)
        if key not in question_session_map:
            continue

        session = next((s for s in sessions if s.id == answer.session_id), None)
        if not session or not session.submitted_at or session.submitted_at < since_date:
            continue

        day = session.submitted_at.date()
        if day not in daily_stats:
            daily_stats[day] = {"attempted": 0, "correct": 0}
        daily_stats[day]["attempted"] += 1
        if answer.is_correct:
            daily_stats[day]["correct"] += 1

    trend = [
        {
            "date": day,
            "attempted": stats["attempted"],
            "correct": stats["correct"],
            "accuracy_pct": (
                round((stats["correct"] / stats["attempted"] * 100), 2)
                if stats["attempted"] > 0
                else 0.0
            ),
        }
        for day, stats in sorted(daily_stats.items())
    ]

    return trend


def _empty_overview() -> dict[str, Any]:
    """Return empty overview structure."""
    return {
        "sessions_completed": 0,
        "questions_seen": 0,
        "questions_answered": 0,
        "correct": 0,
        "accuracy_pct": 0.0,
        "avg_time_sec_per_question": None,
        "by_block": [],
        "weakest_themes": [],
        "trend": [],
        "last_session": None,
    }


def _empty_block_analytics(block: Block) -> dict[str, Any]:
    """Return empty block analytics structure."""
    return {
        "block_id": block.id,
        "block_name": block.name,
        "attempted": 0,
        "correct": 0,
        "accuracy_pct": 0.0,
        "themes": [],
        "trend": [],
    }


def _empty_theme_analytics(theme: Theme, block: Block | None) -> dict[str, Any]:
    """Return empty theme analytics structure."""
    return {
        "theme_id": theme.id,
        "theme_name": theme.title,
        "block_id": theme.block_id,
        "block_name": block.name if block else "",
        "attempted": 0,
        "correct": 0,
        "accuracy_pct": 0.0,
        "trend": [],
        "common_mistakes": [],
    }


async def get_recent_sessions(
    db: AsyncSession, user_id: UUID, limit: int = 10
) -> list[dict[str, Any]]:
    """
    Get recent sessions for a user (both active and completed).

    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of sessions to return

    Returns:
        List of session summaries
    """
    # Get recent sessions (both active and completed)
    sessions_stmt = (
        select(TestSession)
        .where(TestSession.user_id == user_id)
        .order_by(TestSession.started_at.desc())
        .limit(limit)
    )
    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()

    if not sessions:
        return []

    # Get block/theme info from first question of each session
    session_ids = [s.id for s in sessions]
    questions_stmt = (
        select(SessionQuestion)
        .where(SessionQuestion.session_id.in_(session_ids))
        .order_by(SessionQuestion.session_id, SessionQuestion.position)
    )
    questions_result = await db.execute(questions_stmt)
    all_questions = questions_result.scalars().all()

    # Group questions by session and get first question for block/theme
    session_questions_map: dict[UUID, SessionQuestion] = {}
    for q in all_questions:
        if q.session_id not in session_questions_map:
            session_questions_map[q.session_id] = q

    # Get block and theme names
    block_ids = set()
    theme_ids = set()
    for q in session_questions_map.values():
        block_id, theme_id = get_block_theme_from_frozen(q)
        if block_id:
            block_ids.add(block_id)
        if theme_id:
            theme_ids.add(theme_id)

    blocks_map = {}
    if block_ids:
        blocks_stmt = select(Block).where(Block.id.in_(block_ids))
        blocks_result = await db.execute(blocks_stmt)
        blocks_map = {b.id: b for b in blocks_result.scalars().all()}

    themes_map = {}
    if theme_ids:
        themes_stmt = select(Theme).where(Theme.id.in_(theme_ids))
        themes_result = await db.execute(themes_stmt)
        themes_map = {t.id: t for t in themes_result.scalars().all()}

    # Build response
    result = []
    for session in sessions:
        # Determine status
        if session.status == SessionStatus.ACTIVE:
            status = "in_progress"
        elif session.status in (SessionStatus.SUBMITTED, SessionStatus.EXPIRED):
            status = "completed"
        else:
            status = "abandoned"

        # Get block/theme from first question
        first_question = session_questions_map.get(session.id)
        block_id = None
        theme_id = None
        block_name = None
        theme_name = None

        if first_question:
            block_id, theme_id = get_block_theme_from_frozen(first_question)
            if block_id and block_id in blocks_map:
                block_name = blocks_map[block_id].name
            if theme_id and theme_id in themes_map:
                theme_name = themes_map[theme_id].title

        # Build title
        if block_name and theme_name:
            title = f"{block_name} → {theme_name}"
        elif block_name:
            title = block_name
        elif session.blocks_json:
            # Fallback to block codes
            block_codes = session.blocks_json if isinstance(session.blocks_json, list) else []
            title = f"Block{'s' if len(block_codes) > 1 else ''} {', '.join(block_codes)}"
        else:
            title = "Practice Session"

        result.append({
            "session_id": str(session.id),
            "title": title,
            "status": status,
            "score_correct": session.score_correct,
            "score_total": session.score_total,
            "score_pct": float(session.score_pct) if session.score_pct else None,
            "block_id": block_id,
            "theme_id": theme_id,
            "started_at": session.started_at,
            "submitted_at": session.submitted_at,
        })

    return result


async def _compute_avg_time_per_question(
    db: AsyncSession, user_id: UUID, session_ids: list[UUID]
) -> float | None:
    """
    Compute average time per question from telemetry events.
    
    Calculates time between QUESTION_VIEWED and ANSWER_SELECTED events for each question.
    """
    try:
        # Get QUESTION_VIEWED and ANSWER_SELECTED events for these sessions
        events_stmt = select(AttemptEvent).where(
            AttemptEvent.session_id.in_(session_ids),
            AttemptEvent.user_id == user_id,
            AttemptEvent.event_type.in_(["QUESTION_VIEWED", "ANSWER_SELECTED"]),
        ).order_by(AttemptEvent.session_id, AttemptEvent.question_id, AttemptEvent.event_ts)
        
        events_result = await db.execute(events_stmt)
        events = events_result.scalars().all()
        
        if not events:
            return None
        
        # Group events by (session_id, question_id) and calculate time differences
        question_times: dict[tuple[UUID, UUID], list[float]] = {}
        view_times: dict[tuple[UUID, UUID], datetime] = {}
        
        for event in events:
            if not event.question_id:
                continue
            key = (event.session_id, event.question_id)
            
            if event.event_type == "QUESTION_VIEWED":
                # Use client_ts if available, otherwise event_ts
                view_times[key] = event.client_ts or event.event_ts
            elif event.event_type == "ANSWER_SELECTED" and key in view_times:
                # Calculate time difference
                answer_ts = event.client_ts or event.event_ts
                time_diff = (answer_ts - view_times[key]).total_seconds()
                if time_diff > 0 and time_diff < 3600:  # Sanity check: 0-3600 seconds
                    if key not in question_times:
                        question_times[key] = []
                    question_times[key].append(time_diff)
        
        # Calculate average across all questions
        if not question_times:
            return None
        
        all_times = []
        for times in question_times.values():
            # Use first time for each question (in case of multiple answers)
            all_times.append(times[0])
        
        if not all_times:
            return None
        
        avg_time = sum(all_times) / len(all_times)
        return round(avg_time, 2)
    except Exception as e:
        logger.warning(f"Failed to compute avg_time_per_question: {e}")
        return None


async def _compute_common_mistakes(
    db: AsyncSession, user_id: UUID, theme_id: int | None = None
) -> list[dict[str, Any]]:
    """
    Compute common mistakes from mistake_log.
    
    Returns list of mistake types with counts, ordered by frequency.
    """
    try:
        # Build query
        stmt = (
            select(
                MistakeLog.mistake_type,
                func.count(MistakeLog.id).label("count"),
            )
            .where(MistakeLog.user_id == user_id)
            .group_by(MistakeLog.mistake_type)
            .order_by(func.count(MistakeLog.id).desc())
            .limit(10)
        )
        
        if theme_id:
            stmt = stmt.where(MistakeLog.theme_id == theme_id)
        
        result = await db.execute(stmt)
        rows = result.all()
        
        return [
            {
                "mistake_type": row.mistake_type,
                "count": row.count,
            }
            for row in rows
        ]
    except Exception as e:
        logger.warning(f"Failed to compute common_mistakes: {e}")
        return []
