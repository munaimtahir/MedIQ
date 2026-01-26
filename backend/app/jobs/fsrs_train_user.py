"""FSRS per-user optimizer training job."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.registry import create_job_run, update_job_run_status
from app.learning_engine.config import (
    FSRS_DEFAULT_WEIGHTS,
    FSRS_DESIRED_RETENTION,
    FSRS_MIN_LOGS_FOR_TRAINING,
    FSRS_SHRINKAGE_MAX_ALPHA,
    FSRS_SHRINKAGE_TARGET_LOGS,
    FSRS_VALIDATION_SPLIT,
)
from app.models.srs import SRSReviewLog, SRSUserParams

logger = logging.getLogger(__name__)


async def train_fsrs_for_user(
    db: AsyncSession,
    user_id: UUID,
    scheduled_for: datetime | None = None,
) -> dict[str, Any]:
    """
    Train personalized FSRS weights for a user.

    This job:
    1. Loads user's review logs
    2. Splits into train/val (chronological, last 20%)
    3. Fits personalized weights using py-fsrs optimizer
    4. Applies shrinkage (blend with defaults based on log count)
    5. Validates on holdout set
    6. Updates srs_user_params with new weights and metrics

    Args:
        db: Database session
        user_id: User ID
        scheduled_for: Scheduled execution time

    Returns:
        Statistics dictionary
    """
    job_key = "fsrs_train_user"

    # Create job run
    job_run = await create_job_run(db, job_key, scheduled_for)

    try:
        await update_job_run_status(db, job_run.id, "RUNNING")

        # Get user params
        user_params = await db.get(SRSUserParams, user_id)
        if not user_params:
            raise ValueError(f"User params not found for user {user_id}")

        # Check eligibility
        if user_params.n_review_logs < FSRS_MIN_LOGS_FOR_TRAINING.value:
            await update_job_run_status(
                db,
                job_run.id,
                "SUCCEEDED",
                stats={"status": "skipped", "reason": "insufficient_logs", "n_logs": user_params.n_review_logs},
            )
            return {"status": "skipped", "reason": "insufficient_logs"}

        # Load review logs (chronologically ordered)
        stmt = (
            select(SRSReviewLog)
            .where(SRSReviewLog.user_id == user_id)
            .order_by(SRSReviewLog.reviewed_at)
        )
        result = await db.execute(stmt)
        logs = result.scalars().all()

        if len(logs) < FSRS_MIN_LOGS_FOR_TRAINING.value:
            await update_job_run_status(
                db,
                job_run.id,
                "SUCCEEDED",
                stats={"status": "skipped", "reason": "insufficient_logs", "n_logs": len(logs)},
            )
            return {"status": "skipped", "reason": "insufficient_logs"}

        # Split train/val (chronological, last 20% for validation)
        val_size = int(len(logs) * FSRS_VALIDATION_SPLIT.value)
        train_logs = logs[:-val_size] if val_size > 0 else logs
        val_logs = logs[-val_size:] if val_size > 0 else []

        logger.info(f"Training FSRS for user {user_id}: {len(train_logs)} train, {len(val_logs)} val")

        # Convert to py-fsrs ReviewLog format
        from fsrs import ReviewLog as FSRSReviewLog

        train_fsrs_logs = [
            FSRSReviewLog(
                rating=log.rating,
                delta_days=log.delta_days,
                review=log.reviewed_at,
            )
            for log in train_logs
        ]

        val_fsrs_logs = [
            FSRSReviewLog(
                rating=log.rating,
                delta_days=log.delta_days,
                review=log.reviewed_at,
            )
            for log in val_logs
        ]

        # Fit personalized weights
        try:
            from fsrs import Optimizer

            optimizer = Optimizer()
            optimizer.optimize(train_fsrs_logs)
            personalized_weights = optimizer.w

            # Compute shrinkage alpha (blend with defaults based on log count)
            n_logs = len(train_logs)
            alpha = min(
                FSRS_SHRINKAGE_MAX_ALPHA.value,
                max(0.0, (n_logs / FSRS_SHRINKAGE_TARGET_LOGS.value) ** 0.5),
            )

            # Shrinkage: blend personalized with defaults
            default_weights = FSRS_DEFAULT_WEIGHTS.value
            shrunk_weights = [
                alpha * personalized_weights[i] + (1 - alpha) * default_weights[i]
                for i in range(len(default_weights))
            ]

            # Validate on holdout set
            from app.learning_engine.srs.fsrs_adapter import compute_next_state_and_due
            from fsrs import Scheduler

            val_scheduler = Scheduler(parameters=shrunk_weights, desired_retention=FSRS_DESIRED_RETENTION.value)

            val_predictions = []
            val_outcomes = []

            for log in val_logs:
                # Predict retrievability
                # (Simplified - would need full state tracking)
                try:
                    # Get current state for this concept
                    from app.models.srs import SRSConceptState

                    stmt = select(SRSConceptState).where(
                        SRSConceptState.user_id == user_id,
                        SRSConceptState.concept_id == log.concept_id,
                    )
                    result = await db.execute(stmt)
                    state = result.scalar_one_or_none()

                    if state:
                        # Predict retrievability
                        from fsrs import Card

                        card = Card()
                        card.stability = state.stability
                        card.difficulty = state.difficulty
                        card.last_review = state.last_reviewed_at or log.reviewed_at
                        card.due = log.reviewed_at

                        retrievability = val_scheduler.get_retrievability(card, log.reviewed_at)
                        val_predictions.append(retrievability)
                        val_outcomes.append(log.correct)
                except Exception as e:
                    logger.warning(f"Error computing validation prediction: {e}")
                    continue

            # Compute metrics
            metrics = {}
            if val_predictions:
                from app.learning_engine.eval.metrics.calibration import log_loss, brier_score

                metrics["val_logloss"] = log_loss(val_outcomes, val_predictions)
                metrics["val_brier"] = brier_score(val_outcomes, val_predictions)
                metrics["val_size"] = len(val_predictions)

            metrics["train_size"] = len(train_logs)
            metrics["alpha"] = alpha
            metrics["n_logs"] = n_logs

            # Update user params
            user_params.weights_json = shrunk_weights
            user_params.last_trained_at = datetime.utcnow()
            user_params.metrics_json = metrics
            await db.commit()

            stats = {
                "status": "success",
                "n_logs": n_logs,
                "train_size": len(train_logs),
                "val_size": len(val_logs),
                "alpha": alpha,
                "metrics": metrics,
            }

            await update_job_run_status(db, job_run.id, "SUCCEEDED", stats=stats)
            logger.info(f"FSRS training completed for user {user_id}: {metrics}")

            return stats

        except Exception as e:
            logger.error(f"FSRS optimization failed for user {user_id}: {e}", exc_info=True)
            await update_job_run_status(db, job_run.id, "FAILED", error=str(e))
            raise

    except Exception as e:
        logger.error(f"FSRS training job failed: {e}", exc_info=True)
        await update_job_run_status(db, job_run.id, "FAILED", error=str(e))
        raise


async def process_fsrs_training_job(
    db: AsyncSession,
    job_run_id: UUID,
) -> dict[str, Any]:
    """
    Process a FSRS training job run.

    Extracts user_id from job_run metadata and trains.

    Args:
        db: Database session
        job_run_id: Job run ID

    Returns:
        Statistics dictionary
    """
    from app.models.jobs import JobRun

    job_run = await db.get(JobRun, job_run_id)
    if not job_run:
        raise ValueError(f"Job run not found: {job_run_id}")

    # Extract user_id from job metadata (would be stored in stats_json or notes)
    # For now, assume it's in stats_json
    user_id_str = job_run.stats_json.get("user_id")
    if not user_id_str:
        raise ValueError(f"No user_id in job run {job_run_id}")

    user_id = UUID(user_id_str)
    return await train_fsrs_for_user(db, user_id, scheduled_for=job_run.scheduled_for)
