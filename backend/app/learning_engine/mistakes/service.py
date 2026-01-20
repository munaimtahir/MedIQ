"""Mistake classification v0 service with run logging."""

import logging
from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.learning_engine.constants import AlgoKey
from app.learning_engine.mistakes.features import build_features_for_session
from app.learning_engine.mistakes.v0 import classify_session_mistakes_v0
from app.learning_engine.registry import resolve_active
from app.learning_engine.runs import log_run_failure, log_run_start, log_run_success
from app.models.mistakes import MistakeLog
from app.models.session import TestSession

logger = logging.getLogger(__name__)


async def classify_mistakes_v0_for_session(
    db: AsyncSession,
    session_id: UUID,
    trigger: str = "submit",
) -> dict[str, Any]:
    """
    Classify mistakes for all wrong answers in a session.

    This is a BEST-EFFORT operation - failures should not block session submission.

    Workflow:
    1. Resolve active mistakes v0 version and params
    2. Start algo run logging
    3. Extract features from session and telemetry
    4. Classify wrong answers using rule-based precedence
    5. Bulk upsert into mistake_log
    6. Log run success with counts

    Args:
        db: Database session
        session_id: Session ID
        trigger: Run trigger source (e.g., "submit", "manual")

    Returns:
        Summary dictionary with counts and run_id, or error dict
    """
    try:
        # Resolve active version and params
        version, params_obj = await resolve_active(db, AlgoKey.MISTAKES.value)
        if not version or not params_obj:
            logger.warning("No active mistakes algorithm version or params found")
            return {
                "total_wrong": 0,
                "classified": 0,
                "error": "no_active_algo",
            }

        params = params_obj.params_json

        # Get session
        session = await db.get(TestSession, session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return {
                "total_wrong": 0,
                "classified": 0,
                "error": "session_not_found",
            }

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

        # Extract features for all attempts
        features_list = await build_features_for_session(db, session_id)

        if not features_list:
            await log_run_success(
                db,
                run_id=run.id,
                output_summary={
                    "total_wrong": 0,
                    "classified": 0,
                    "reason": "no_features",
                },
            )
            return {
                "total_wrong": 0,
                "classified": 0,
                "run_id": str(run.id),
            }

        # Classify wrong answers
        classifications = classify_session_mistakes_v0(features_list, params)

        if not classifications:
            await log_run_success(
                db,
                run_id=run.id,
                output_summary={
                    "total_wrong": 0,
                    "classified": 0,
                    "reason": "no_wrong_answers",
                },
            )
            return {
                "total_wrong": 0,
                "classified": 0,
                "run_id": str(run.id),
            }

        # Prepare bulk upsert data
        mistake_records = []
        counts_by_type = defaultdict(int)

        for features, classification in classifications:
            counts_by_type[classification.mistake_type] += 1

            record = {
                "user_id": session.user_id,
                "session_id": session_id,
                "question_id": features.question_id,
                "position": features.position,
                "year": features.year,
                "block_id": features.block_id,
                "theme_id": features.theme_id,
                "is_correct": features.is_correct,
                "mistake_type": classification.mistake_type,
                "severity": classification.severity,
                "evidence_json": classification.evidence,
                "algo_version_id": version.id,
                "params_id": params_obj.id,
                "run_id": run.id,
            }
            mistake_records.append(record)

        # Bulk upsert (idempotent)
        if mistake_records:
            stmt = insert(MistakeLog).values(mistake_records)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_mistake_log_session_question",
                set_={
                    "mistake_type": stmt.excluded.mistake_type,
                    "severity": stmt.excluded.severity,
                    "evidence_json": stmt.excluded.evidence_json,
                    "algo_version_id": stmt.excluded.algo_version_id,
                    "params_id": stmt.excluded.params_id,
                    "run_id": stmt.excluded.run_id,
                    "year": stmt.excluded.year,
                    "block_id": stmt.excluded.block_id,
                    "theme_id": stmt.excluded.theme_id,
                    "position": stmt.excluded.position,
                },
            )
            await db.execute(stmt)
            await db.commit()

        # Log success
        output_summary = {
            "total_wrong": len(classifications),
            "classified": len(mistake_records),
            "counts_by_type": dict(counts_by_type),
        }

        await log_run_success(
            db,
            run_id=run.id,
            output_summary=output_summary,
        )

        return {
            "total_wrong": len(classifications),
            "classified": len(mistake_records),
            "counts_by_type": dict(counts_by_type),
            "run_id": str(run.id),
        }

    except Exception as e:
        logger.error(f"Failed to classify mistakes for session {session_id}: {e}")

        # Log failure if run was started
        if "run" in locals():
            try:
                await log_run_failure(db, run_id=run.id, error_message=str(e))
            except Exception as log_error:
                logger.error(f"Failed to log run failure: {log_error}")

        # Best-effort: return error dict, do not raise
        return {
            "total_wrong": 0,
            "classified": 0,
            "error": str(e),
        }
