"""Difficulty Calibration v0 service (ELO-lite)."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.learning_engine.constants import AlgoKey
from app.learning_engine.registry import resolve_active
from app.learning_engine.runs import log_run_failure, log_run_start, log_run_success
from app.models.learning_difficulty import QuestionDifficulty
from app.models.learning_mastery import UserThemeMastery
from app.models.session import SessionAnswer, SessionQuestion, TestSession

logger = logging.getLogger(__name__)


def compute_student_rating(
    strategy: str,
    params: dict[str, Any],
    mastery_score: float | None = None,
) -> float:
    """
    Compute student rating based on strategy.
    
    Args:
        strategy: "fixed" or "mastery_mapped"
        params: Algorithm parameters
        mastery_score: User's mastery score for theme (if available)
    
    Returns:
        Student rating
    """
    baseline = params.get("baseline_rating", 1000)
    
    if strategy == "fixed":
        return baseline
    
    elif strategy == "mastery_mapped":
        if mastery_score is None:
            return baseline
        
        rating_map = params.get("mastery_rating_map", {"min": 800, "max": 1200})
        min_rating = rating_map["min"]
        max_rating = rating_map["max"]
        
        # Map mastery_score (0..1) to rating range
        student_rating = min_rating + (mastery_score * (max_rating - min_rating))
        return student_rating
    
    return baseline


def compute_elo_update(
    question_rating: float,
    student_rating: float,
    actual: int,  # 0 or 1
    k_factor: float,
    rating_scale: float,
) -> tuple[float, float, float]:
    """
    Compute ELO-lite rating update.
    
    Args:
        question_rating: Current question rating
        student_rating: Student's rating
        actual: 1 if correct, 0 if incorrect
        k_factor: ELO k-factor
        rating_scale: Rating scale constant
    
    Returns:
        Tuple of (new_rating, delta, expected)
    """
    # Expected probability (logistic function)
    expected = 1.0 / (1.0 + 10.0 ** ((question_rating - student_rating) / rating_scale))
    
    # Delta
    delta = k_factor * (actual - expected)
    
    # New rating
    new_rating = question_rating + delta
    
    return new_rating, delta, expected


async def update_question_difficulty_v0_for_session(
    db: AsyncSession,
    session_id: UUID,
    trigger: str = "submit",
) -> dict[str, Any]:
    """
    Update question difficulty ratings for all answered questions in a session.
    
    Uses ELO-lite algorithm with configurable student rating strategies.
    
    Args:
        db: Database session
        session_id: Session ID
        trigger: Run trigger source
    
    Returns:
        Summary dictionary with update counts
    """
    try:
        # Resolve active version and params
        version, params_obj = await resolve_active(db, AlgoKey.DIFFICULTY.value)
        if not version or not params_obj:
            logger.warning("No active difficulty algorithm version or params found")
            return {"questions_updated": 0, "error": "no_active_algo"}
        
        params = params_obj.params_json
        
        # Get session
        session = await db.get(TestSession, session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return {"questions_updated": 0, "error": "session_not_found"}
        
        # Start run logging
        run = await log_run_start(
            db,
            algo_version_id=version.id,
            params_id=params_obj.id,
            user_id=session.user_id,
            session_id=session_id,
            trigger=trigger,
            input_summary={"session_id": str(session_id)},
        )
        
        # Get all answers for this session
        answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session_id)
        answers_result = await db.execute(answers_stmt)
        answers = answers_result.scalars().all()
        
        if not answers:
            await log_run_success(
                db,
                run_id=run.id,
                output_summary={"questions_updated": 0, "reason": "no_answers"},
            )
            return {"questions_updated": 0, "avg_delta": 0.0}
        
        # Get session questions (for theme info)
        questions_stmt = select(SessionQuestion).where(SessionQuestion.session_id == session_id)
        questions_result = await db.execute(questions_stmt)
        session_questions = {sq.question_id: sq for sq in questions_result.scalars().all()}
        
        # Get mastery scores for user (if mastery_mapped strategy)
        strategy = params.get("student_rating_strategy", "fixed")
        mastery_scores = {}
        if strategy == "mastery_mapped":
            mastery_stmt = select(UserThemeMastery).where(
                UserThemeMastery.user_id == session.user_id
            )
            mastery_result = await db.execute(mastery_stmt)
            for mastery in mastery_result.scalars().all():
                mastery_scores[mastery.theme_id] = float(mastery.mastery_score)
        
        # Get existing difficulty ratings
        question_ids = [a.question_id for a in answers]
        difficulty_stmt = select(QuestionDifficulty).where(
            QuestionDifficulty.question_id.in_(question_ids)
        )
        difficulty_result = await db.execute(difficulty_stmt)
        existing_difficulties = {d.question_id: d for d in difficulty_result.scalars().all()}
        
        # Compute updates
        k_factor = params.get("k_factor", 16)
        rating_scale = params.get("rating_scale", 400)
        baseline_rating = params.get("baseline_rating", 1000)
        
        updates = []
        total_delta = 0.0
        
        for answer in answers:
            # Skip if no selected answer
            if answer.selected_index is None:
                continue
            
            # Determine actual (1 if correct, 0 if incorrect)
            actual = 1 if answer.is_correct else 0
            
            # Get theme from session question
            sq = session_questions.get(answer.question_id)
            theme_id = None
            if sq:
                if sq.question_version:
                    theme_id = sq.question_version.theme_id
                elif sq.snapshot_json:
                    theme_id = sq.snapshot_json.get("theme_id")
            
            # Compute student rating
            mastery_score = mastery_scores.get(theme_id) if theme_id else None
            student_rating = compute_student_rating(strategy, params, mastery_score)
            
            # Get current question rating
            existing = existing_difficulties.get(answer.question_id)
            current_rating = float(existing.rating) if existing else baseline_rating
            
            # Compute ELO update
            new_rating, delta, expected = compute_elo_update(
                current_rating,
                student_rating,
                actual,
                k_factor,
                rating_scale,
            )
            
            total_delta += abs(delta)
            
            # Compute new aggregates
            if existing:
                new_attempts = existing.attempts + 1
                new_correct = existing.correct + actual
            else:
                new_attempts = 1
                new_correct = actual
            
            new_p_correct = new_correct / new_attempts if new_attempts > 0 else None
            
            # Build breakdown
            breakdown = {
                "actual": actual,
                "expected": round(expected, 4),
                "delta": round(delta, 2),
                "student_rating": round(student_rating, 2),
                "theme_id": theme_id,
                "mastery_score": round(mastery_score, 4) if mastery_score is not None else None,
            }
            
            updates.append({
                "question_id": answer.question_id,
                "rating": round(new_rating, 2),
                "attempts": new_attempts,
                "correct": new_correct,
                "p_correct": round(new_p_correct, 4) if new_p_correct is not None else None,
                "last_updated_at": datetime.utcnow(),
                "algo_version_id": version.id,
                "params_id": params_obj.id,
                "run_id": run.id,
                "breakdown_json": breakdown,
            })
        
        # Bulk upsert
        if updates:
            stmt = insert(QuestionDifficulty).values(updates)
            stmt = stmt.on_conflict_do_update(
                index_elements=["question_id"],
                set_={
                    "rating": stmt.excluded.rating,
                    "attempts": stmt.excluded.attempts,
                    "correct": stmt.excluded.correct,
                    "p_correct": stmt.excluded.p_correct,
                    "last_updated_at": stmt.excluded.last_updated_at,
                    "algo_version_id": stmt.excluded.algo_version_id,
                    "params_id": stmt.excluded.params_id,
                    "run_id": stmt.excluded.run_id,
                    "breakdown_json": stmt.excluded.breakdown_json,
                }
            )
            await db.execute(stmt)
            await db.commit()
        
        avg_delta = total_delta / len(updates) if updates else 0.0
        
        # Log success
        await log_run_success(
            db,
            run_id=run.id,
            output_summary={
                "questions_updated": len(updates),
                "avg_delta": round(avg_delta, 2),
            },
        )
        
        return {
            "questions_updated": len(updates),
            "avg_delta": round(avg_delta, 2),
            "run_id": str(run.id),
        }
    
    except Exception as e:
        logger.error(f"Failed to update difficulty for session {session_id}: {e}")
        # Best effort - don't block session submission
        return {"questions_updated": 0, "error": str(e)}
