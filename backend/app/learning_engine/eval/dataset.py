"""Dataset builder for evaluation harness."""

import logging
from collections.abc import Iterator
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question_cms import Question
from app.models.session import SessionAnswer, TestSession

logger = logging.getLogger(__name__)


class EvalEvent(BaseModel):
    """Canonical evaluation event model."""

    # Core identifiers
    event_id: UUID
    user_id: UUID
    session_id: UUID
    question_id: UUID
    timestamp: datetime

    # Outcome
    is_correct: bool | None  # None if not answered

    # Telemetry (optional)
    response_time_ms: int | None = None
    option_change_count: int | None = None
    mark_for_review: bool | None = None
    pause_blur_count: int | None = None

    # Context
    year: int | None = None
    block_id: UUID | None = None
    theme_id: UUID | None = None
    cognitive_level: str | None = None
    question_difficulty: str | None = None

    # Bandit OPE (optional, for future)
    action_propensity: float | None = None  # Probability of action under logging policy
    action_taken: str | None = None  # Action identifier

    # Sequence
    event_sequence: int | None = None  # Order within user/session


class DatasetSpec(BaseModel):
    """Dataset specification for evaluation."""

    time_min: datetime
    time_max: datetime
    years: list[int] | None = None  # Filter by academic years
    block_ids: list[UUID] | None = None  # Filter by blocks
    theme_ids: list[UUID] | None = None  # Filter by themes
    cohort_filters: dict[str, Any] | None = None  # Additional cohort filters
    split_strategy: str = "time"  # "time" or "user_holdout"
    split_config: dict[str, Any] | None = None  # Split-specific config


async def build_eval_dataset(
    db: AsyncSession,
    spec: DatasetSpec,
) -> Iterator[EvalEvent]:
    """
    Build evaluation dataset from Postgres.

    Fetches canonical answer events in time range, joins to question tags,
    and yields events ordered by user_id, timestamp, event_sequence.

    Args:
        db: Database session
        spec: Dataset specification

    Yields:
        EvalEvent instances in order
    """
    logger.info(f"Building eval dataset: {spec.time_min} to {spec.time_max}")

    # Build base query for session answers
    stmt = (
        select(
            SessionAnswer.id,
            SessionAnswer.session_id,
            SessionAnswer.question_id,
            SessionAnswer.is_correct,
            SessionAnswer.answered_at,
            SessionAnswer.changed_count,
            SessionAnswer.marked_for_review,
            TestSession.user_id,
            TestSession.year,
            TestSession.started_at,
        )
        .join(TestSession, SessionAnswer.session_id == TestSession.id)
        .where(
            and_(
                SessionAnswer.answered_at >= spec.time_min,
                SessionAnswer.answered_at <= spec.time_max,
                SessionAnswer.selected_index.isnot(None),  # Only answered questions
            )
        )
    )

    # Apply filters
    if spec.years:
        stmt = stmt.where(TestSession.year.in_(spec.years))

    # Order by user, timestamp
    stmt = stmt.order_by(TestSession.user_id, SessionAnswer.answered_at)

    result = await db.execute(stmt)
    rows = result.all()

    logger.info(f"Found {len(rows)} answered events")

    # Fetch question metadata in batch
    question_ids = list(set(row.question_id for row in rows))
    questions_stmt = select(Question).where(Question.id.in_(question_ids))
    questions_result = await db.execute(questions_stmt)
    questions = {q.id: q for q in questions_result.scalars().all()}

    # Build event sequence counter per user
    user_sequence = {}
    event_count = 0

    for row in rows:
        user_id = row.user_id
        if user_id not in user_sequence:
            user_sequence[user_id] = 0
        user_sequence[user_id] += 1

        # Get question metadata
        question = questions.get(row.question_id)

        # Build EvalEvent
        event = EvalEvent(
            event_id=row.id,
            user_id=user_id,
            session_id=row.session_id,
            question_id=row.question_id,
            timestamp=row.answered_at or row.started_at,
            is_correct=row.is_correct,
            option_change_count=row.changed_count,
            mark_for_review=row.marked_for_review,
            year=row.year,
            block_id=question.block_id if question else None,
            theme_id=question.theme_id if question else None,
            cognitive_level=question.cognitive_level if question else None,
            question_difficulty=question.difficulty if question else None,
            event_sequence=user_sequence[user_id],
        )

        # TODO: Extract response_time_ms and pause_blur_count from AttemptEvent if available
        # For now, these remain None

        event_count += 1
        if event_count % 1000 == 0:
            logger.debug(f"Processed {event_count} events...")

        yield event

    logger.info(f"Dataset build complete: {event_count} events")


def apply_split(
    events: list[EvalEvent],
    strategy: str,
    config: dict[str, Any] | None = None,
) -> tuple[list[EvalEvent], list[EvalEvent]]:
    """
    Apply split strategy to events.

    Args:
        events: List of events (should be sorted by timestamp)
        strategy: "time" or "user_holdout"
        config: Split-specific configuration

    Returns:
        Tuple of (train_events, eval_events)
    """
    config = config or {}

    if strategy == "time":
        # Time-based split: train window then eval window
        split_ratio = config.get("train_ratio", 0.8)
        split_idx = int(len(events) * split_ratio)
        return events[:split_idx], events[split_idx:]

    elif strategy == "user_holdout":
        # Per-user last-K holdout
        holdout_ratio = config.get("holdout_ratio", 0.2)
        holdout_count = config.get("holdout_count", None)

        # Group by user
        user_events: dict[UUID, list[EvalEvent]] = {}
        for event in events:
            if event.user_id not in user_events:
                user_events[event.user_id] = []
            user_events[event.user_id].append(event)

        train_events = []
        eval_events = []

        for user_id, user_event_list in user_events.items():
            # Sort by timestamp
            user_event_list.sort(key=lambda e: e.timestamp)

            if holdout_count:
                # Holdout last N events
                split_idx = max(0, len(user_event_list) - holdout_count)
            else:
                # Holdout last X%
                split_idx = int(len(user_event_list) * (1 - holdout_ratio))

            train_events.extend(user_event_list[:split_idx])
            eval_events.extend(user_event_list[split_idx:])

        return train_events, eval_events

    else:
        raise ValueError(f"Unknown split strategy: {strategy}")
