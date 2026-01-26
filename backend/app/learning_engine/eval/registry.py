"""Registry for evaluation runs, metrics, and artifacts."""

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.eval import EvalArtifact, EvalCurve, EvalMetric, EvalRun

logger = logging.getLogger(__name__)

# Storage path for artifacts
ARTIFACTS_BASE = Path("backend/artifacts/eval")


def get_artifact_path(run_id: UUID) -> Path:
    """Get storage path for a run's artifacts."""
    return ARTIFACTS_BASE / str(run_id)


async def create_eval_run(
    db: AsyncSession,
    suite_name: str,
    suite_versions: dict[str, str],
    dataset_spec: dict[str, Any],
    config: dict[str, Any],
    git_sha: str | None = None,
    random_seed: int | None = None,
    notes: str | None = None,
) -> EvalRun:
    """
    Create a new evaluation run.

    Args:
        db: Database session
        suite_name: Suite name (e.g., "bkt_v1")
        suite_versions: Dictionary of algorithm versions
        dataset_spec: Dataset specification
        config: Evaluation configuration
        git_sha: Git commit SHA
        random_seed: Random seed for reproducibility
        notes: Optional notes

    Returns:
        Created EvalRun
    """
    eval_run = EvalRun(
        status="QUEUED",
        suite_name=suite_name,
        suite_versions=suite_versions,
        dataset_spec=dataset_spec,
        config=config,
        git_sha=git_sha,
        random_seed=random_seed,
        notes=notes,
    )

    db.add(eval_run)
    await db.commit()
    await db.refresh(eval_run)

    logger.info(f"Created eval run: {eval_run.id}")
    return eval_run


async def update_eval_run_status(
    db: AsyncSession,
    run_id: UUID,
    status: str,
    error: str | None = None,
) -> EvalRun:
    """
    Update evaluation run status.

    Args:
        db: Database session
        run_id: Run ID
        status: New status (QUEUED, RUNNING, SUCCEEDED, FAILED)
        error: Error message if failed

    Returns:
        Updated EvalRun
    """
    eval_run = await db.get(EvalRun, run_id)
    if not eval_run:
        raise ValueError(f"Eval run not found: {run_id}")

    eval_run.status = status
    if error:
        eval_run.error = error

    if status == "RUNNING":
        from datetime import datetime

        eval_run.started_at = datetime.utcnow()
    elif status in ("SUCCEEDED", "FAILED"):
        from datetime import datetime

        eval_run.finished_at = datetime.utcnow()

    await db.commit()
    await db.refresh(eval_run)
    return eval_run


async def save_metric(
    db: AsyncSession,
    run_id: UUID,
    metric_name: str,
    value: float,
    n: int,
    scope_type: str = "GLOBAL",
    scope_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> EvalMetric:
    """
    Save a computed metric.

    Args:
        db: Database session
        run_id: Run ID
        metric_name: Metric name
        value: Metric value
        n: Number of observations
        scope_type: Scope type
        scope_id: Scope identifier
        extra: Extra metadata

    Returns:
        Created EvalMetric
    """
    metric = EvalMetric(
        run_id=run_id,
        metric_name=metric_name,
        scope_type=scope_type,
        scope_id=scope_id,
        value=value,
        n=n,
        extra=extra,
    )

    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    return metric


async def save_artifact(
    db: AsyncSession,
    run_id: UUID,
    artifact_type: str,
    content: str,
    filename: str,
) -> EvalArtifact:
    """
    Save an artifact (report, summary, etc.).

    Args:
        db: Database session
        run_id: Run ID
        artifact_type: Artifact type (REPORT_MD, RELIABILITY_BINS, etc.)
        content: Artifact content (string)
        filename: Filename

    Returns:
        Created EvalArtifact
    """
    # Create directory
    artifact_dir = get_artifact_path(run_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Write file
    artifact_path = artifact_dir / filename
    artifact_path.write_text(content, encoding="utf-8")

    # Save record
    artifact = EvalArtifact(
        run_id=run_id,
        artifact_type=artifact_type,
        path=str(artifact_path),
    )

    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact


async def save_curve(
    db: AsyncSession,
    run_id: UUID,
    curve_name: str,
    data: dict[str, Any],
) -> EvalCurve:
    """
    Save curve data.

    Args:
        db: Database session
        run_id: Run ID
        curve_name: Curve name
        data: Curve data points

    Returns:
        Created EvalCurve
    """
    curve = EvalCurve(
        run_id=run_id,
        curve_name=curve_name,
        data=data,
    )

    db.add(curve)
    await db.commit()
    await db.refresh(curve)
    return curve


async def get_eval_run(db: AsyncSession, run_id: UUID) -> EvalRun | None:
    """Get evaluation run by ID."""
    return await db.get(EvalRun, run_id)


async def list_eval_runs(
    db: AsyncSession,
    suite_name: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[EvalRun]:
    """
    List evaluation runs.

    Args:
        db: Database session
        suite_name: Filter by suite name
        status: Filter by status
        limit: Maximum number of results

    Returns:
        List of EvalRun
    """
    stmt = select(EvalRun)

    if suite_name:
        stmt = stmt.where(EvalRun.suite_name == suite_name)
    if status:
        stmt = stmt.where(EvalRun.status == status)

    stmt = stmt.order_by(EvalRun.created_at.desc()).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())
