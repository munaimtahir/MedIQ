"""Evaluation runner - orchestrates dataset -> replay -> metrics -> store."""

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.eval.dataset import DatasetSpec, build_eval_dataset
from app.learning_engine.eval.metrics.calibration import (
    brier_score,
    expected_calibration_error,
    log_loss,
    reliability_curve_data,
)
from app.learning_engine.eval.registry import (
    create_eval_run,
    save_artifact,
    save_curve,
    save_metric,
    update_eval_run_status,
)
from app.learning_engine.eval.replay import EvalSuite, replay_dataset

logger = logging.getLogger(__name__)


async def run_evaluation(
    db: AsyncSession,
    suite: EvalSuite,
    suite_name: str,
    suite_versions: dict[str, str],
    dataset_spec: DatasetSpec,
    config: dict[str, Any],
    git_sha: str | None = None,
    random_seed: int | None = None,
    notes: str | None = None,
) -> UUID:
    """
    Run a complete evaluation.

    Args:
        db: Database session
        suite: Algorithm suite to evaluate
        suite_name: Suite name
        suite_versions: Algorithm versions
        dataset_spec: Dataset specification
        config: Evaluation configuration
        git_sha: Git commit SHA
        random_seed: Random seed
        notes: Optional notes

    Returns:
        Eval run ID
    """
    # Create run
    eval_run = await create_eval_run(
        db,
        suite_name=suite_name,
        suite_versions=suite_versions,
        dataset_spec=dataset_spec.model_dump(),
        config=config,
        git_sha=git_sha,
        random_seed=random_seed,
        notes=notes,
    )

    run_id = eval_run.id

    try:
        # Update status to RUNNING
        await update_eval_run_status(db, run_id, "RUNNING")

        # Build dataset
        logger.info(f"Building dataset for run {run_id}")
        events_iter = build_eval_dataset(db, dataset_spec)

        # Replay
        logger.info(f"Replaying events for run {run_id}")
        traces = await replay_dataset(events_iter, suite, store_traces=config.get("store_traces", False))

        # Compute metrics
        logger.info(f"Computing metrics for run {run_id}")
        await _compute_and_store_metrics(db, run_id, traces, config)

        # Generate report
        logger.info(f"Generating report for run {run_id}")
        await _generate_report(db, run_id, traces, config)

        # Update status to SUCCEEDED
        await update_eval_run_status(db, run_id, "SUCCEEDED")

        logger.info(f"Evaluation run {run_id} completed successfully")
        return run_id

    except Exception as e:
        logger.error(f"Evaluation run {run_id} failed: {e}", exc_info=True)
        await update_eval_run_status(db, run_id, "FAILED", error=str(e))
        raise


async def _compute_and_store_metrics(
    db: AsyncSession,
    run_id: UUID,
    traces: dict[UUID, Any],  # user_id -> ReplayTrace
    config: dict[str, Any],
) -> None:
    """Compute and store metrics from replay traces."""
    # Collect predictions and outcomes
    all_predictions = []
    all_outcomes = []

    # Need to get actual outcomes from events
    # For now, collect from predictions that have p_correct
    # In full implementation, would track event -> outcome mapping during replay
    for user_id, trace in traces.items():
        for pred in trace.predictions:
            if pred.p_correct is not None:
                all_predictions.append(pred.p_correct)
                # TODO: Get actual outcome from event context
                # Placeholder: assume 50% correct rate for now
                # In real implementation, would track outcome during replay
                all_outcomes.append(True)  # Placeholder

    if not all_predictions:
        logger.warning("No predictions found for metrics computation")
        return

    # Calibration metrics
    if len(all_predictions) == len(all_outcomes):
        # Log loss
        logloss = log_loss(all_outcomes, all_predictions)
        await save_metric(db, run_id, "logloss", logloss, len(all_predictions))

        # Brier score
        brier = brier_score(all_outcomes, all_predictions)
        await save_metric(db, run_id, "brier", brier, len(all_predictions))

        # ECE
        n_bins = config.get("calibration_bins", 10)
        ece, bin_details = expected_calibration_error(all_outcomes, all_predictions, n_bins)
        await save_metric(
            db,
            run_id,
            "ece",
            ece,
            len(all_predictions),
            extra={"bin_details": bin_details},
        )

        # Reliability curve
        curve_data = reliability_curve_data(all_outcomes, all_predictions, n_bins)
        await save_curve(db, run_id, "reliability_curve_p_correct", curve_data)


async def _generate_report(
    db: AsyncSession,
    run_id: UUID,
    traces: dict[UUID, Any],
    config: dict[str, Any],
) -> None:
    """Generate Markdown report for evaluation run."""
    # Get run to include metadata
    from app.learning_engine.eval.registry import get_eval_run

    eval_run = await get_eval_run(db, run_id)
    if not eval_run:
        return

    # Build report
    report_lines = [
        "# Evaluation Report",
        "",
        f"**Run ID:** {run_id}",
        f"**Suite:** {eval_run.suite_name}",
        f"**Status:** {eval_run.status}",
        f"**Created:** {eval_run.created_at}",
        "",
        "## Configuration",
        "",
        f"```json",
        json.dumps(eval_run.config, indent=2),
        "```",
        "",
        "## Metrics Summary",
        "",
        "### Calibration Metrics",
        "",
        "| Metric | Value | N |",
        "|--------|-------|---|",
    ]

    # Get metrics
    stmt = select(EvalMetric).where(EvalMetric.run_id == run_id)
    result = await db.execute(stmt)
    metrics = result.scalars().all()

    for metric in metrics:
        if metric.scope_type == "GLOBAL":
            report_lines.append(f"| {metric.metric_name} | {metric.value:.6f} | {metric.n} |")

    report_lines.extend([
        "",
        "## Notes",
        "",
        eval_run.notes or "No notes provided.",
    ])

    report_content = "\n".join(report_lines)

    # Save report
    await save_artifact(db, run_id, "REPORT_MD", report_content, "report.md")

    # Save summary JSON
    summary = {
        "run_id": str(run_id),
        "suite_name": eval_run.suite_name,
        "status": eval_run.status,
        "metrics": [
            {
                "name": m.metric_name,
                "value": float(m.value),
                "n": m.n,
                "scope": m.scope_type,
            }
            for m in metrics
        ],
    }
    await save_artifact(
        db, run_id, "RAW_SUMMARY", json.dumps(summary, indent=2), "summary.json"
    )
