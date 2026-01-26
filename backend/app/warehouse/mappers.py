"""Mapping layer: Postgres → Warehouse Export Rows.

Maps database models to stable export row contracts.
Uses iterators to avoid loading all rows in memory.
"""

import logging
from collections.abc import Iterator
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.algo_runtime import AlgoRuntimeConfig
from app.models.bkt import BKTSkillParams, MasterySnapshot
from app.models.difficulty import DifficultyUpdateLog
from app.models.learning_difficulty import QuestionDifficulty
from app.models.learning_revision import RevisionQueue
from app.models.question_cms import Question
from app.models.session import AttemptEvent, SessionAnswer, TestSession
from app.warehouse.contracts import (
    AttemptExportRow,
    EventExportRow,
    MasterySnapshotExportRow,
    RevisionQueueDailyExportRow,
)

logger = logging.getLogger(__name__)


def _get_algo_profile_and_versions(
    db: Session, attempt_timestamp: datetime
) -> tuple[str, dict[str, str]]:
    """
    Get algorithm profile and versions snapshot at a given timestamp.

    For now, returns current runtime config. In future, could query historical config.
    """
    config = db.query(AlgoRuntimeConfig).order_by(AlgoRuntimeConfig.updated_at.desc()).first()
    if not config:
        return "V1_PRIMARY", {}

    profile = config.active_profile.value if hasattr(config.active_profile, "value") else str(config.active_profile)
    overrides = config.config_json.get("overrides", {})
    
    # Derive algo versions from profile and overrides
    algo_versions = {
        "mastery": overrides.get("mastery", "v1"),
        "revision": overrides.get("revision", "v1"),
        "adaptive": overrides.get("adaptive", "v1"),
        "difficulty": overrides.get("difficulty", "v1"),
        "mistakes": overrides.get("mistakes", "v1"),
    }

    return profile, algo_versions


def map_attempts(
    db: Session,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> Iterator[AttemptExportRow]:
    """
    Map SessionAnswer rows to AttemptExportRow.

    Joins with TestSession, Question, and optionally difficulty/ELO ratings.
    """
    from app.models.session import SessionQuestion

    query = (
        select(
            SessionAnswer.id,
            SessionAnswer.session_id,
            SessionAnswer.question_id,
            SessionAnswer.selected_index,
            SessionAnswer.is_correct,
            SessionAnswer.answered_at,
            SessionAnswer.changed_count,
            SessionAnswer.marked_for_review,
            TestSession.user_id,
            TestSession.year,
            TestSession.started_at,
            TestSession.algo_profile_at_start,
            TestSession.algo_overrides_at_start,
            Question.theme_id,
            Question.block_id,
            Question.year_id,
            Question.concept_id,
            SessionQuestion.snapshot_json,
        )
        .join(TestSession, SessionAnswer.session_id == TestSession.id)
        .join(Question, SessionAnswer.question_id == Question.id)
        .outerjoin(
            SessionQuestion,
            and_(
                SessionQuestion.session_id == SessionAnswer.session_id,
                SessionQuestion.question_id == SessionAnswer.question_id,
            ),
        )
        .where(SessionAnswer.selected_index.isnot(None))  # Only answered questions
    )

    if range_start:
        query = query.where(SessionAnswer.answered_at >= range_start)
    if range_end:
        query = query.where(SessionAnswer.answered_at <= range_end)

    query = query.order_by(SessionAnswer.answered_at)

    result = db.execute(query)
    rows = result.all()

    logger.info(f"Mapping {len(rows)} attempts to export rows")

    # Batch fetch difficulty and ELO ratings
    question_ids = list(set(row.question_id for row in rows))
    user_ids = list(set(row.user_id for row in rows))

    # Get difficulty snapshots (latest per question)
    difficulty_query = (
        select(QuestionDifficulty.question_id, QuestionDifficulty.rating)
        .where(QuestionDifficulty.question_id.in_(question_ids))
    )
    difficulty_rows = db.execute(difficulty_query).all()
    difficulty_map = {row.question_id: float(row.rating) for row in difficulty_rows}

    # Get ELO ratings from DifficultyUpdateLog (most recent per attempt)
    # Note: This is approximate - we use the most recent update log entry before/at attempt time
    elo_query = (
        select(
            DifficultyUpdateLog.attempt_id,
            DifficultyUpdateLog.user_rating_pre,
            DifficultyUpdateLog.user_rating_post,
            DifficultyUpdateLog.q_rating_pre,
            DifficultyUpdateLog.q_rating_post,
        )
        .where(
            and_(
                DifficultyUpdateLog.attempt_id.isnot(None),
                DifficultyUpdateLog.user_id.in_(user_ids),
            )
        )
        .order_by(DifficultyUpdateLog.id.desc())
    )
    elo_rows = db.execute(elo_query).all()
    elo_map = {
        row.attempt_id: {
            "user_before": float(row.user_rating_pre),
            "user_after": float(row.user_rating_post),
            "question_before": float(row.q_rating_pre),
            "question_after": float(row.q_rating_post),
        }
        for row in elo_rows
        if row.attempt_id
    }

    for row in rows:
        # Get algo profile and versions (use session snapshot if available)
        algo_profile = row.algo_profile_at_start or "V1_PRIMARY"
        algo_overrides = row.algo_overrides_at_start or {}
        algo_versions = {
            "mastery": algo_overrides.get("mastery", "v1"),
            "revision": algo_overrides.get("revision", "v1"),
            "adaptive": algo_overrides.get("adaptive", "v1"),
            "difficulty": algo_overrides.get("difficulty", "v1"),
            "mistakes": algo_overrides.get("mistakes", "v1"),
        }

        # Get ELO ratings if available
        elo_data = elo_map.get(row.id, {})
        elo_user_before = elo_data.get("user_before")
        elo_user_after = elo_data.get("user_after")
        elo_question_before = elo_data.get("question_before")
        elo_question_after = elo_data.get("question_after")

        # Get difficulty snapshot
        difficulty_value = difficulty_map.get(row.question_id)
        difficulty_snapshot = None
        if difficulty_value is not None:
            # Map numeric difficulty to label (simplified)
            if difficulty_value < 1000:
                difficulty_snapshot = "EASY"
            elif difficulty_value < 1500:
                difficulty_snapshot = "MEDIUM"
            else:
                difficulty_snapshot = "HARD"

        # Calculate time_spent_ms (if we have session start and answer time)
        time_spent_ms = None
        if row.answered_at and row.started_at:
            delta = row.answered_at - row.started_at
            time_spent_ms = int(delta.total_seconds() * 1000)

        # Get correct_index from snapshot if available
        correct_index = None
        if row.snapshot_json and isinstance(row.snapshot_json, dict):
            correct_index = row.snapshot_json.get("correct_index")

        # Use theme_id as concept_id fallback if concept_id missing
        concept_id = row.concept_id or row.theme_id

        yield AttemptExportRow(
            attempt_id=str(row.id),
            user_id=str(row.user_id),
            session_id=str(row.session_id),
            question_id=str(row.question_id),
            attempted_at=row.answered_at or row.created_at,
            is_correct=row.is_correct or False,
            concept_id=concept_id,
            theme_id=row.theme_id,
            block_id=row.block_id,
            year=row.year_id or row.year,
            selected_index=row.selected_index,
            correct_index=correct_index,
            time_spent_ms=time_spent_ms,
            changed_answer_count=row.changed_count,
            marked_for_review=row.marked_for_review,
            difficulty_snapshot=difficulty_snapshot,
            difficulty_value=difficulty_value,
            elo_user_before=elo_user_before,
            elo_user_after=elo_user_after,
            elo_question_before=elo_question_before,
            elo_question_after=elo_question_after,
            algo_profile=algo_profile,
            algo_versions=algo_versions,
        )


def map_events(
    db: Session,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> Iterator[EventExportRow]:
    """
    Map AttemptEvent rows to EventExportRow.
    """
    query = select(AttemptEvent).where(AttemptEvent.event_ts.isnot(None))

    if range_start:
        query = query.where(AttemptEvent.event_ts >= range_start)
    if range_end:
        query = query.where(AttemptEvent.event_ts <= range_end)

    query = query.order_by(AttemptEvent.event_ts)

    result = db.execute(query)
    events = result.scalars().all()

    logger.info(f"Mapping {len(events)} events to export rows")

    for event in events:
        client_meta = {
            "source": event.source,
            "client_ts": event.client_ts.isoformat() if event.client_ts else None,
            "seq": event.seq,
            "event_version": event.event_version,
        }

        yield EventExportRow(
            event_id=str(event.id),
            user_id=str(event.user_id),
            session_id=str(event.session_id),
            event_type=event.event_type,
            event_at=event.event_ts,
            payload=event.payload_json or {},
            client_meta=client_meta,
            ingested_at=event.created_at,
        )


def map_mastery_snapshots(
    db: Session,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> Iterator[MasterySnapshotExportRow]:
    """
    Map MasterySnapshot (BKT) rows to MasterySnapshotExportRow.

    Uses concept_id from snapshot (UUID). For v1, concept_id may be theme-based.
    """
    query = select(MasterySnapshot).where(MasterySnapshot.created_at.isnot(None))

    if range_start:
        query = query.where(MasterySnapshot.created_at >= range_start)
    if range_end:
        query = query.where(MasterySnapshot.created_at <= range_end)

    query = query.order_by(MasterySnapshot.created_at)

    result = db.execute(query)
    snapshots = result.scalars().all()

    logger.info(f"Mapping {len(snapshots)} mastery snapshots to export rows")

    # Get algo profile and versions
    algo_profile, algo_versions = _get_algo_profile_and_versions(db, datetime.now())

    # Batch fetch BKT parameters if available
    concept_ids = list(set(snapshot.concept_id for snapshot in snapshots))

    bkt_params_query = (
        select(BKTSkillParams.concept_id, BKTSkillParams.p_L0, BKTSkillParams.p_T, BKTSkillParams.p_S, BKTSkillParams.p_G)
        .where(
            and_(
                BKTSkillParams.concept_id.in_(concept_ids),
                BKTSkillParams.is_active == True,
            )
        )
    )
    bkt_params_rows = db.execute(bkt_params_query).all()
    bkt_params_map = {
        row.concept_id: {
            "p_L0": float(row.p_L0),
            "p_T": float(row.p_T),
            "p_S": float(row.p_S),
            "p_G": float(row.p_G),
        }
        for row in bkt_params_rows
    }

    for snapshot in snapshots:
        # Get BKT parameters if available
        bkt_params = bkt_params_map.get(snapshot.concept_id, {})

        # Use concept_id as-is (UUID string)
        concept_id = str(snapshot.concept_id)

        # Note: correct_total and last_attempt_at would need to be computed from attempts
        # For now, we use n_attempts and leave correct_total as 0 (would need join)
        yield MasterySnapshotExportRow(
            snapshot_id=str(snapshot.id),
            user_id=str(snapshot.user_id),
            concept_id=concept_id,
            snapshot_at=snapshot.created_at,  # Use created_at as snapshot timestamp
            mastery_prob=float(snapshot.p_mastery),
            attempts_total=snapshot.n_attempts,
            correct_total=0,  # Would need to compute from attempts
            last_attempt_at=None,  # Would need to join with attempts
            bkt_params=bkt_params,
            algo_profile=algo_profile,
            algo_version_mastery=algo_versions.get("mastery", "bkt_v1"),
        )


def map_revision_queue_daily(
    db: Session,
    date_range_start: date | None = None,
    date_range_end: date | None = None,
) -> Iterator[RevisionQueueDailyExportRow]:
    """
    Map RevisionQueue rows to daily snapshots.

    Aggregates per user per day.
    """
    query = select(RevisionQueue).where(RevisionQueue.due_date.isnot(None))

    if date_range_start:
        query = query.where(RevisionQueue.due_date >= date_range_start)
    if date_range_end:
        query = query.where(RevisionQueue.due_date <= date_range_end)

    query = query.order_by(RevisionQueue.user_id, RevisionQueue.due_date)

    result = db.execute(query)
    rows = result.scalars().all()

    logger.info(f"Mapping {len(rows)} revision queue entries to daily snapshots")

    # Group by user_id and due_date
    from collections import defaultdict

    daily_snapshots: dict[tuple[UUID, date], dict[str, Any]] = defaultdict(
        lambda: {
            "due_today_count": 0,
            "overdue_count": 0,
            "next_due_at": None,
        }
    )

    today = date.today()

    for row in rows:
        key = (row.user_id, row.due_date)
        snapshot = daily_snapshots[key]

        if row.due_date == today:
            snapshot["due_today_count"] += 1
        elif row.due_date < today:
            snapshot["overdue_count"] += 1

        # Track earliest due date for next_due_at
        if row.due_date >= today:
            if snapshot["next_due_at"] is None or row.due_date < snapshot["next_due_at"]:
                snapshot["next_due_at"] = row.due_date

    # Get algo profile and versions
    algo_profile, algo_versions = _get_algo_profile_and_versions(db, datetime.now())

    for (user_id, snapshot_date), data in daily_snapshots.items():
        # Convert date to datetime for next_due_at
        next_due_at = None
        if data["next_due_at"]:
            next_due_at = datetime.combine(data["next_due_at"], datetime.min.time())

        yield RevisionQueueDailyExportRow(
            snapshot_date=snapshot_date,
            user_id=str(user_id),
            due_today_count=data["due_today_count"],
            overdue_count=data["overdue_count"],
            next_due_at=next_due_at,
            algo_profile=algo_profile,
            algo_version_revision=algo_versions.get("revision", "fsrs_v1"),
        )
