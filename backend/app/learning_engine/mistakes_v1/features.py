"""Extended feature extraction for Mistake Engine v1."""

import logging
from datetime import datetime, timedelta
from statistics import median
from uuid import UUID

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.mistakes.features import (
    AttemptFeatures,
    build_features_for_session,
    compute_blur_count,
    compute_change_count,
    compute_mark_for_review,
    compute_time_spent_by_question,
)
from app.learning_engine.mistakes_v1.schemas import AttemptFeaturesV1
from app.models.learning_difficulty import QuestionDifficulty
from app.models.mistakes import MistakeLog
from app.models.question_cms import Question
from app.models.session import SessionAnswer, TestSession

logger = logging.getLogger(__name__)


async def compute_user_rolling_stats(
    db: AsyncSession,
    user_id: UUID,
    current_time: datetime,
    n_attempts: int = 10,
    lookback_days: int = 30,
) -> tuple[float | None, float | None]:
    """
    Compute user rolling accuracy and median time from recent attempts.

    Args:
        db: Database session
        user_id: User ID
        current_time: Current timestamp (for lookback window)
        n_attempts: Number of recent attempts to consider
        lookback_days: Maximum days to look back

    Returns:
        Tuple of (rolling_accuracy, rolling_median_time_seconds) or (None, None) if insufficient data
    """
    lookback_start = current_time - timedelta(days=lookback_days)

    # Get recent session answers for this user
    stmt = (
        select(SessionAnswer)
        .join(TestSession)
        .where(
            TestSession.user_id == user_id,
            SessionAnswer.answered_at >= lookback_start,
            SessionAnswer.selected_index.isnot(None),  # Only answered questions
        )
        .order_by(SessionAnswer.answered_at.desc())
        .limit(n_attempts)
    )

    result = await db.execute(stmt)
    answers = result.scalars().all()

    if len(answers) < 3:  # Need at least 3 attempts for meaningful stats
        return None, None

    # Compute accuracy
    correct_count = sum(1 for a in answers if a.is_correct)
    accuracy = correct_count / len(answers)

    # Compute median time (need to join with telemetry or use session timing)
    # For now, use a simplified approach: estimate from session duration
    # TODO: Could enhance with actual attempt-level timing from telemetry
    median_time = None

    return accuracy, median_time


async def compute_cohort_time_stats(
    db: AsyncSession,
    current_time: datetime,
    lookback_days: int = 30,
) -> tuple[float | None, float | None]:
    """
    Compute cohort-level median and std dev of response times.

    Args:
        db: Database session
        current_time: Current timestamp
        lookback_days: Lookback window

    Returns:
        Tuple of (median_seconds, std_seconds) or (None, None) if insufficient data
    """
    lookback_start = current_time - timedelta(days=lookback_days)

    # Get time spent from recent sessions (using QUESTION_VIEWED events would be better)
    # For now, use a simplified approach
    # TODO: Enhance with actual telemetry aggregation
    return None, None


async def get_question_difficulty(
    db: AsyncSession,
    question_id: UUID,
) -> float | None:
    """
    Get question difficulty from Elo rating or fallback to initial difficulty.

    Args:
        db: Database session
        question_id: Question ID

    Returns:
        Difficulty rating (Elo) or None
    """
    # Try Elo rating first
    stmt = select(QuestionDifficulty).where(QuestionDifficulty.question_id == question_id)
    result = await db.execute(stmt)
    difficulty = result.scalar_one_or_none()

    if difficulty and difficulty.rating is not None:
        return float(difficulty.rating)

    # Fallback to question's initial difficulty field (if available)
    stmt = select(Question).where(Question.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()

    if question and question.difficulty:
        # Map string difficulty to numeric (simple mapping)
        difficulty_map = {"easy": 800.0, "medium": 1000.0, "hard": 1200.0}
        return difficulty_map.get(question.difficulty.lower(), 1000.0)

    return None


async def compute_zscore(
    value: float | None,
    median_val: float | None,
    std_val: float | None,
) -> float | None:
    """
    Compute z-score, handling missing values.

    Args:
        value: Value to compute z-score for
        median_val: Median (or mean) of distribution
        std_val: Standard deviation

    Returns:
        Z-score or None if insufficient data
    """
    if value is None or median_val is None or std_val is None or std_val == 0:
        return None

    return (value - median_val) / std_val


async def extract_features_v1_for_attempt(
    db: AsyncSession,
    session_id: UUID,
    question_id: UUID,
    user_id: UUID | None = None,
) -> AttemptFeaturesV1 | None:
    """
    Extract v1 features for a single attempt.

    Args:
        db: Database session
        session_id: Session ID
        question_id: Question ID
        user_id: User ID (if not provided, will be fetched from session)

    Returns:
        AttemptFeaturesV1 or None if attempt not found
    """
    # Get session
    session = await db.get(TestSession, session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        return None

    if user_id is None:
        user_id = session.user_id

    # Get answer
    stmt = select(SessionAnswer).where(
        SessionAnswer.session_id == session_id,
        SessionAnswer.question_id == question_id,
    )
    result = await db.execute(stmt)
    answer = result.scalar_one_or_none()

    if not answer or answer.selected_index is None:
        logger.warning(f"Answer not found for session {session_id}, question {question_id}")
        return None

    # Get base features using existing v0 feature extraction
    base_features_list = await build_features_for_session(db, session_id)
    base_features = next((f for f in base_features_list if f.question_id == question_id), None)

    if not base_features:
        logger.warning(f"Base features not found for question {question_id}")
        return None

    # Get question metadata
    question = await db.get(Question, question_id)
    cognitive_level = question.cognitive_level if question else None

    # Get difficulty
    question_difficulty = await get_question_difficulty(db, question_id)

    # Compute time z-scores (simplified - would need user/cohort stats)
    response_time_seconds = base_features.time_spent_sec
    response_time_zscore_user = None
    response_time_zscore_cohort = None

    # TODO: Implement proper z-score computation with user/cohort distributions
    # For now, use percentiles from telemetry if available

    # Get user rolling stats
    current_time = answer.answered_at or datetime.utcnow()
    user_rolling_accuracy, user_rolling_median_time = await compute_user_rolling_stats(
        db, user_id, current_time
    )

    # Compute session pacing (simplified)
    session_pacing_indicator = None

    # Determine first answer correctness (would need telemetry to track first answer)
    first_answer_correct = None  # TODO: Track from ANSWER_SELECTED events

    # Build v1 features
    features = AttemptFeaturesV1(
        question_id=question_id,
        session_id=session_id,
        user_id=user_id,
        position=base_features.position,
        is_correct=base_features.is_correct,
        answered_at=base_features.answered_at,
        response_time_seconds=response_time_seconds,
        response_time_zscore_user=response_time_zscore_user,
        response_time_zscore_cohort=response_time_zscore_cohort,
        time_remaining_at_answer=base_features.remaining_sec_at_answer,
        changed_answer_count=base_features.change_count,
        first_answer_correct=first_answer_correct,
        final_answer_correct=base_features.is_correct,
        mark_for_review_used=base_features.mark_for_review_used,
        pause_blur_count=base_features.blur_count,
        question_difficulty=question_difficulty,
        cognitive_level=cognitive_level,
        block_id=base_features.block_id,
        theme_id=base_features.theme_id,
        year=base_features.year,
        user_rolling_accuracy_last_n=user_rolling_accuracy,
        user_rolling_median_time_last_n=user_rolling_median_time,
        session_pacing_indicator=session_pacing_indicator,
    )

    return features


async def extract_features_v1_for_session(
    db: AsyncSession,
    session_id: UUID,
) -> list[AttemptFeaturesV1]:
    """
    Extract v1 features for all attempts in a session.

    Args:
        db: Database session
        session_id: Session ID

    Returns:
        List of AttemptFeaturesV1
    """
    # Get session
    session = await db.get(TestSession, session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        return []

    # Get all answers
    stmt = select(SessionAnswer).where(
        SessionAnswer.session_id == session_id,
        SessionAnswer.selected_index.isnot(None),
    )
    result = await db.execute(stmt)
    answers = result.scalars().all()

    features_list = []

    for answer in answers:
        features = await extract_features_v1_for_attempt(
            db, session_id, answer.question_id, session.user_id
        )
        if features:
            features_list.append(features)

    return features_list


def features_to_dict(features: AttemptFeaturesV1) -> dict[str, float | int | str | bool | None]:
    """
    Convert AttemptFeaturesV1 to dictionary for model input.

    Handles None values and type conversions.

    Args:
        features: AttemptFeaturesV1 instance

    Returns:
        Dictionary of feature values
    """
    return {
        "position": features.position if features.position is not None else -1,
        "is_correct": int(features.is_correct),
        "response_time_seconds": features.response_time_seconds if features.response_time_seconds is not None else 0.0,
        "response_time_zscore_user": features.response_time_zscore_user if features.response_time_zscore_user is not None else 0.0,
        "response_time_zscore_cohort": features.response_time_zscore_cohort if features.response_time_zscore_cohort is not None else 0.0,
        "time_remaining_at_answer": features.time_remaining_at_answer if features.time_remaining_at_answer is not None else -1.0,
        "changed_answer_count": features.changed_answer_count,
        "first_answer_correct": int(features.first_answer_correct) if features.first_answer_correct is not None else -1,
        "final_answer_correct": int(features.final_answer_correct),
        "mark_for_review_used": int(features.mark_for_review_used),
        "pause_blur_count": features.pause_blur_count,
        "question_difficulty": features.question_difficulty if features.question_difficulty is not None else 1000.0,
        "cognitive_level": features.cognitive_level or "unknown",
        "year": features.year if features.year is not None else -1,
        "user_rolling_accuracy_last_n": features.user_rolling_accuracy_last_n if features.user_rolling_accuracy_last_n is not None else 0.5,
        "user_rolling_median_time_last_n": features.user_rolling_median_time_last_n if features.user_rolling_median_time_last_n is not None else 0.0,
        "session_pacing_indicator": features.session_pacing_indicator if features.session_pacing_indicator is not None else 0.0,
    }
