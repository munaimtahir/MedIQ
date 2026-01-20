"""Analytics service for computing student performance metrics."""

import logging
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, cast, Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question_cms import Question
from app.models.session import SessionAnswer, SessionQuestion, SessionStatus, TestSession
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
            answer = next((a for a in answers if a.question_id == sq.question_id and a.session_id == sq.session_id), None)
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
            "accuracy_pct": round((stats["correct"] / stats["attempted"] * 100), 2) if stats["attempted"] > 0 else 0.0,
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
            
            answer = next((a for a in answers if a.question_id == sq.question_id and a.session_id == sq.session_id), None)
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
                "accuracy_pct": round((stats["correct"] / stats["attempted"] * 100), 2) if stats["attempted"] > 0 else 0.0,
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
            "accuracy_pct": round((stats["correct"] / stats["attempted"] * 100), 2) if stats["attempted"] > 0 else 0.0,
        }
        for day, stats in sorted(daily_stats.items())
    ]
    
    # Last session
    last_session = max(sessions, key=lambda s: s.submitted_at or datetime.min)
    last_session_summary = {
        "session_id": last_session.id,
        "score_pct": float(last_session.score_pct or 0.0),
        "submitted_at": last_session.submitted_at,
    } if last_session else None
    
    return {
        "sessions_completed": sessions_completed,
        "questions_seen": questions_seen,
        "questions_answered": questions_answered,
        "correct": correct,
        "accuracy_pct": accuracy_pct,
        "avg_time_sec_per_question": None,  # TODO: compute from telemetry
        "by_block": by_block,
        "weakest_themes": weakest_themes,
        "trend": trend,
        "last_session": last_session_summary,
    }


async def get_block_analytics(db: AsyncSession, user_id: UUID, block_id: int) -> dict[str, Any] | None:
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
            
            answer = next((a for a in answers if a.question_id == sq.question_id and a.session_id == sq.session_id), None)
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
            "accuracy_pct": round((stats["correct"] / stats["attempted"] * 100), 2) if stats["attempted"] > 0 else 0.0,
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


async def get_theme_analytics(db: AsyncSession, user_id: UUID, theme_id: int) -> dict[str, Any] | None:
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
    
    return {
        "theme_id": theme_id,
        "theme_name": theme.title,
        "block_id": theme.block_id,
        "block_name": block.name if block else "",
        "attempted": attempted,
        "correct": correct,
        "accuracy_pct": accuracy_pct,
        "trend": trend,
        "common_mistakes": [],  # Placeholder for future
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
            "accuracy_pct": round((stats["correct"] / stats["attempted"] * 100), 2) if stats["attempted"] > 0 else 0.0,
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
