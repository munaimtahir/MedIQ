"""Mastery v0 computation service."""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.learning_engine.constants import AlgoKey
from app.learning_engine.registry import resolve_active
from app.learning_engine.runs import log_run_failure, log_run_start, log_run_success
from app.models.learning_mastery import UserThemeMastery
from app.models.session import SessionAnswer, SessionQuestion, SessionStatus, TestSession

logger = logging.getLogger(__name__)


def get_block_theme_from_frozen(session_question: SessionQuestion) -> tuple[int | None, int | None, int | None]:
    """
    Extract block_id, theme_id, and year from frozen question content.
    
    Tries question_version first, falls back to snapshot_json.
    Returns (block_id, theme_id, year).
    """
    # Try version first
    if session_question.question_version:
        return (
            session_question.question_version.block_id,
            session_question.question_version.theme_id,
            session_question.question_version.year,
        )
    
    # Fallback to snapshot
    if session_question.snapshot_json:
        return (
            session_question.snapshot_json.get("block_id"),
            session_question.snapshot_json.get("theme_id"),
            session_question.snapshot_json.get("year"),
        )
    
    return None, None, None


def compute_recency_weighted_accuracy(
    attempts: list[dict],
    params: dict[str, Any],
    current_time: datetime,
) -> tuple[float, dict[str, Any]]:
    """
    Compute mastery score using recency-weighted accuracy.
    
    Args:
        attempts: List of attempt dicts with 'is_correct', 'answered_at', 'difficulty'
        params: Algorithm parameters
        current_time: Reference time for recency calculation
    
    Returns:
        Tuple of (mastery_score, breakdown_dict)
    """
    if not attempts:
        return 0.0, {"reason": "no_attempts"}
    
    recency_buckets = params.get("recency_buckets", [
        {"days": 7, "weight": 0.50},
        {"days": 30, "weight": 0.30},
        {"days": 90, "weight": 0.20},
    ])
    use_difficulty = params.get("use_difficulty", False)
    difficulty_weights = params.get("difficulty_weights", {
        "easy": 0.90,
        "medium": 1.00,
        "hard": 1.10,
    })
    
    # Organize attempts into buckets
    bucket_data = {}
    for bucket in recency_buckets:
        days = bucket["days"]
        weight = bucket["weight"]
        cutoff = current_time - timedelta(days=days)
        
        # Find attempts in this bucket
        bucket_attempts = [
            a for a in attempts
            if a["answered_at"] and a["answered_at"] >= cutoff
        ]
        
        if not bucket_attempts:
            bucket_data[f"{days}d"] = {
                "attempts": 0,
                "correct": 0,
                "accuracy": 0.0,
                "weight": weight,
                "contribution": 0.0,
            }
            continue
        
        # Compute accuracy for this bucket
        correct = sum(1 for a in bucket_attempts if a["is_correct"])
        total = len(bucket_attempts)
        
        # Apply difficulty weighting if enabled and available
        if use_difficulty:
            weighted_correct = 0.0
            weighted_total = 0.0
            for a in bucket_attempts:
                diff = a.get("difficulty", "medium").lower()
                diff_weight = difficulty_weights.get(diff, 1.0)
                weighted_total += diff_weight
                if a["is_correct"]:
                    weighted_correct += diff_weight
            
            bucket_accuracy = weighted_correct / weighted_total if weighted_total > 0 else 0.0
        else:
            bucket_accuracy = correct / total if total > 0 else 0.0
        
        contribution = bucket_accuracy * weight
        
        bucket_data[f"{days}d"] = {
            "attempts": total,
            "correct": correct,
            "accuracy": round(bucket_accuracy, 4),
            "weight": weight,
            "contribution": round(contribution, 4),
        }
    
    # Sum contributions
    mastery_score = sum(b["contribution"] for b in bucket_data.values())
    
    breakdown = {
        "total_attempts": len(attempts),
        "buckets": bucket_data,
        "mastery_score": round(mastery_score, 4),
        "use_difficulty": use_difficulty,
    }
    
    return round(mastery_score, 4), breakdown


async def collect_theme_attempts(
    db: AsyncSession,
    user_id: UUID,
    theme_id: int,
    lookback_days: int,
    current_time: datetime,
) -> list[dict]:
    """
    Collect all attempts for a user-theme combination within lookback window.
    
    Args:
        db: Database session
        user_id: User ID
        theme_id: Theme ID
        lookback_days: Days to look back
        current_time: Reference time
    
    Returns:
        List of attempt dictionaries
    """
    cutoff = current_time - timedelta(days=lookback_days)
    
    # Get all completed sessions for user within lookback
    sessions_stmt = select(TestSession).where(
        TestSession.user_id == user_id,
        TestSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.EXPIRED]),
        TestSession.submitted_at >= cutoff,
    )
    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()
    
    if not sessions:
        return []
    
    session_ids = [s.id for s in sessions]
    
    # Get questions for this theme
    questions_stmt = select(SessionQuestion).where(
        SessionQuestion.session_id.in_(session_ids)
    )
    questions_result = await db.execute(questions_stmt)
    all_questions = questions_result.scalars().all()
    
    # Filter to theme
    theme_questions = [
        sq for sq in all_questions
        if get_block_theme_from_frozen(sq)[1] == theme_id
    ]
    
    if not theme_questions:
        return []
    
    # Get answers
    question_keys = [(sq.session_id, sq.question_id) for sq in theme_questions]
    answers_stmt = select(SessionAnswer).where(
        SessionAnswer.session_id.in_(session_ids)
    )
    answers_result = await db.execute(answers_stmt)
    answers = answers_result.scalars().all()
    
    # Build attempts list
    attempts = []
    for sq in theme_questions:
        # Find corresponding answer
        answer = next(
            (a for a in answers if a.session_id == sq.session_id and a.question_id == sq.question_id),
            None
        )
        
        if answer:
            # Extract difficulty from snapshot if available
            difficulty = None
            if sq.snapshot_json:
                difficulty = sq.snapshot_json.get("difficulty")
            elif sq.question_version:
                difficulty = sq.question_version.difficulty
            
            attempts.append({
                "session_id": sq.session_id,
                "question_id": sq.question_id,
                "is_correct": answer.is_correct or False,
                "answered_at": answer.answered_at,
                "difficulty": difficulty,
            })
    
    return attempts


async def compute_mastery_for_theme(
    db: AsyncSession,
    user_id: UUID,
    year: int,
    block_id: int,
    theme_id: int,
    params: dict[str, Any],
    current_time: datetime,
) -> dict[str, Any]:
    """
    Compute mastery score for a single user-theme combination.
    
    Args:
        db: Database session
        user_id: User ID
        year: Academic year
        block_id: Block ID
        theme_id: Theme ID
        params: Algorithm parameters
        current_time: Reference time
    
    Returns:
        Dictionary with mastery data
    """
    lookback_days = params.get("lookback_days", 90)
    min_attempts = params.get("min_attempts", 5)
    
    # Collect attempts
    attempts = await collect_theme_attempts(db, user_id, theme_id, lookback_days, current_time)
    
    # Compute aggregates
    attempts_total = len(attempts)
    correct_total = sum(1 for a in attempts if a["is_correct"])
    accuracy_pct = round((correct_total / attempts_total * 100), 2) if attempts_total > 0 else 0.0
    
    last_attempt_at = None
    if attempts:
        last_attempt_at = max(a["answered_at"] for a in attempts if a["answered_at"])
    
    # Compute mastery score
    if attempts_total < min_attempts:
        # Not enough data
        mastery_score = 0.0
        breakdown = {
            "reason": "insufficient_attempts",
            "required": min_attempts,
            "actual": attempts_total,
        }
    else:
        mastery_score, breakdown = compute_recency_weighted_accuracy(attempts, params, current_time)
    
    return {
        "user_id": user_id,
        "year": year,
        "block_id": block_id,
        "theme_id": theme_id,
        "attempts_total": attempts_total,
        "correct_total": correct_total,
        "accuracy_pct": accuracy_pct,
        "mastery_score": mastery_score,
        "last_attempt_at": last_attempt_at,
        "breakdown_json": breakdown,
    }


async def upsert_mastery_records(
    db: AsyncSession,
    records: list[dict[str, Any]],
    algo_version_id: UUID,
    params_id: UUID,
    run_id: UUID,
) -> int:
    """
    Upsert mastery records into the database.
    
    Args:
        db: Database session
        records: List of mastery record dictionaries
        algo_version_id: Algorithm version ID
        params_id: Parameter set ID
        run_id: Run ID
    
    Returns:
        Number of records upserted
    """
    if not records:
        return 0
    
    # Add provenance fields
    for record in records:
        record["algo_version_id"] = algo_version_id
        record["params_id"] = params_id
        record["run_id"] = run_id
        record["computed_at"] = datetime.utcnow()
    
    # Upsert using PostgreSQL INSERT ... ON CONFLICT
    stmt = insert(UserThemeMastery).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "theme_id"],
        set_={
            "year": stmt.excluded.year,
            "block_id": stmt.excluded.block_id,
            "attempts_total": stmt.excluded.attempts_total,
            "correct_total": stmt.excluded.correct_total,
            "accuracy_pct": stmt.excluded.accuracy_pct,
            "mastery_score": stmt.excluded.mastery_score,
            "last_attempt_at": stmt.excluded.last_attempt_at,
            "computed_at": stmt.excluded.computed_at,
            "algo_version_id": stmt.excluded.algo_version_id,
            "params_id": stmt.excluded.params_id,
            "run_id": stmt.excluded.run_id,
            "breakdown_json": stmt.excluded.breakdown_json,
        }
    )
    
    await db.execute(stmt)
    await db.commit()
    
    return len(records)


async def recompute_mastery_v0_for_user(
    db: AsyncSession,
    user_id: UUID,
    theme_ids: list[int] | None = None,
) -> dict[str, Any]:
    """
    Recompute mastery scores for a user across all themes (or specified themes).
    
    Args:
        db: Database session
        user_id: User ID
        theme_ids: Optional list of theme IDs to recompute (default: all themes user has attempted)
    
    Returns:
        Summary dictionary with counts and stats
    """
    # Resolve active version and params
    version, params_obj = await resolve_active(db, AlgoKey.MASTERY.value)
    if not version or not params_obj:
        raise ValueError("No active mastery algorithm version or params found")
    
    params = params_obj.params_json
    current_time = datetime.utcnow()
    lookback_days = params.get("lookback_days", 90)
    
    # Start run logging
    run = await log_run_start(
        db,
        algo_version_id=version.id,
        params_id=params_obj.id,
        user_id=user_id,
        trigger="api",
        input_summary={
            "user_id": str(user_id),
            "theme_ids": theme_ids,
            "lookback_days": lookback_days,
        }
    )
    
    try:
        # Get all themes user has attempted
        cutoff = current_time - timedelta(days=lookback_days)
        sessions_stmt = select(TestSession).where(
            TestSession.user_id == user_id,
            TestSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.EXPIRED]),
            TestSession.submitted_at >= cutoff,
        )
        sessions_result = await db.execute(sessions_stmt)
        sessions = sessions_result.scalars().all()
        
        if not sessions:
            await log_run_success(
                db,
                run_id=run.id,
                output_summary={"themes_computed": 0, "reason": "no_completed_sessions"}
            )
            return {"themes_computed": 0, "records_upserted": 0}
        
        session_ids = [s.id for s in sessions]
        
        # Get all questions from these sessions
        questions_stmt = select(SessionQuestion).where(
            SessionQuestion.session_id.in_(session_ids)
        )
        questions_result = await db.execute(questions_stmt)
        all_questions = questions_result.scalars().all()
        
        # Extract unique (year, block_id, theme_id) combinations
        theme_combos = set()
        for sq in all_questions:
            block_id, theme_id, year = get_block_theme_from_frozen(sq)
            if theme_id and (theme_ids is None or theme_id in theme_ids):
                # Default year if not available
                if year is None:
                    year = 1  # Default to year 1 if not specified
                theme_combos.add((year, block_id, theme_id))
        
        # Compute mastery for each theme
        records = []
        for year, block_id, theme_id in theme_combos:
            if block_id is None:
                continue  # Skip if no block_id available
            
            record = await compute_mastery_for_theme(
                db, user_id, year, block_id, theme_id, params, current_time
            )
            records.append(record)
        
        # Upsert records
        num_upserted = await upsert_mastery_records(
            db, records, version.id, params_obj.id, run.id
        )
        
        # Log success
        await log_run_success(
            db,
            run_id=run.id,
            output_summary={
                "themes_computed": len(records),
                "records_upserted": num_upserted,
                "user_id": str(user_id),
            }
        )
        
        return {
            "themes_computed": len(records),
            "records_upserted": num_upserted,
            "run_id": str(run.id),
        }
    
    except Exception as e:
        logger.error(f"Failed to compute mastery for user {user_id}: {e}")
        await log_run_failure(db, run_id=run.id, error_message=str(e))
        raise
