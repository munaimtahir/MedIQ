"""IRT calibration run registry: update status, store params/abilities, artifacts."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.difficulty import DifficultyQuestionRating
from app.models.irt import IrtCalibrationRun, IrtItemFit, IrtItemParams, IrtUserAbility

logger = logging.getLogger(__name__)

ARTIFACTS_BASE = Path("backend/artifacts/irt")


def get_irt_artifact_path(run_id: UUID) -> Path:
    return ARTIFACTS_BASE / str(run_id)


async def get_irt_run(db: AsyncSession, run_id: UUID) -> IrtCalibrationRun | None:
    return await db.get(IrtCalibrationRun, run_id)


async def create_irt_run(
    db: AsyncSession,
    model_type: str,
    dataset_spec: dict[str, Any],
    seed: int,
    notes: str | None = None,
) -> IrtCalibrationRun:
    run = IrtCalibrationRun(
        model_type=model_type,
        dataset_spec=dataset_spec,
        status="QUEUED",
        seed=seed,
        notes=notes,
    )
    db.add(run)
    await db.flush()
    await db.commit()
    await db.refresh(run)
    return run


async def list_irt_runs(
    db: AsyncSession,
    model_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[IrtCalibrationRun]:
    stmt = select(IrtCalibrationRun)
    if model_type:
        stmt = stmt.where(IrtCalibrationRun.model_type == model_type)
    if status:
        stmt = stmt.where(IrtCalibrationRun.status == status)
    stmt = stmt.order_by(IrtCalibrationRun.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_irt_run_status(
    db: AsyncSession,
    run_id: UUID,
    status: str,
    *,
    error: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    metrics: dict[str, Any] | None = None,
    artifact_paths: dict[str, str] | None = None,
    eval_run_id: UUID | None = None,
) -> IrtCalibrationRun:
    run = await db.get(IrtCalibrationRun, run_id)
    if not run:
        raise ValueError(f"IRT run not found: {run_id}")
    run.status = status
    if error is not None:
        run.error = error
    if started_at is not None:
        run.started_at = started_at
    if finished_at is not None:
        run.finished_at = finished_at
    if metrics is not None:
        run.metrics = metrics
    if artifact_paths is not None:
        run.artifact_paths = artifact_paths
    if eval_run_id is not None:
        run.eval_run_id = eval_run_id
    await db.commit()
    await db.refresh(run)
    return run


async def store_item_params(
    db: AsyncSession,
    run_id: UUID,
    item_a: dict[UUID, float],
    item_b: dict[UUID, float],
    item_c: dict[UUID, float],
    item_a_se: dict[UUID, float],
    item_b_se: dict[UUID, float],
    item_c_se: dict[UUID, float],
    flags: dict[UUID, dict[str, Any]],
) -> None:
    await db.execute(delete(IrtItemParams).where(IrtItemParams.run_id == run_id))
    for qid in item_a:
        params = IrtItemParams(
            id=uuid.uuid4(),
            run_id=run_id,
            question_id=qid,
            a=item_a[qid],
            b=item_b[qid],
            c=item_c.get(qid) if item_c else None,
            a_se=item_a_se.get(qid),
            b_se=item_b_se.get(qid),
            c_se=item_c_se.get(qid) if item_c_se else None,
            flags=flags.get(qid),
        )
        db.add(params)
    await db.commit()


async def store_user_abilities(
    db: AsyncSession,
    run_id: UUID,
    user_theta: dict[UUID, float],
    user_theta_se: dict[UUID, float],
) -> None:
    await db.execute(delete(IrtUserAbility).where(IrtUserAbility.run_id == run_id))
    for uid in user_theta:
        ab = IrtUserAbility(
            id=uuid.uuid4(),
            run_id=run_id,
            user_id=uid,
            theta=user_theta[uid],
            theta_se=user_theta_se.get(uid),
        )
        db.add(ab)
    await db.commit()


async def store_item_fit(
    db: AsyncSession,
    run_id: UUID,
    question_id: UUID,
    loglik: float | None,
    infit: float | None,
    outfit: float | None,
    info_curve_summary: dict[str, Any] | None,
) -> None:
    row = IrtItemFit(
        id=uuid.uuid4(),
        run_id=run_id,
        question_id=question_id,
        loglik=loglik,
        infit=infit,
        outfit=outfit,
        info_curve_summary=info_curve_summary,
    )
    db.add(row)
    await db.commit()


async def fetch_elo_difficulty_global(db: AsyncSession) -> dict[UUID, float]:
    """Fetch GLOBAL Elo difficulty (rating) per question for cold-start b."""
    stmt = select(DifficultyQuestionRating.question_id, DifficultyQuestionRating.rating).where(
        DifficultyQuestionRating.scope_type == "GLOBAL",
        DifficultyQuestionRating.scope_id.is_(None),
    )
    result = await db.execute(stmt)
    return {r.question_id: float(r.rating) for r in result.all()}
