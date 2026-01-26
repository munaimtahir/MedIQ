"""Rank prediction admin API — shadow/offline only."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.learning_engine.rank.config import get_rank_config
from app.learning_engine.rank.model_v1 import compute_rank_snapshot
from app.security.exam_mode_gate import require_not_exam_mode
from app.learning_engine.runtime import (
    MODULE_RANK,
    get_algo_runtime_config,
    get_rank_mode,
    is_rank_enabled_for_admin,
    is_safe_mode_freeze_updates,
)
from app.models.rank import (
    RankActivationEvent,
    RankModelRun,
    RankPredictionSnapshot,
    RankRunStatus,
    RankSnapshotStatus,
)
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


# --- Schemas ---


class RankRunCreate(BaseModel):
    cohort_key: str
    reason: str
    confirmation_phrase: str | None = None


class RankRunResponse(BaseModel):
    id: str
    cohort_key: str
    model_version: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    metrics: dict[str, Any] | None
    error: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class RankSnapshotResponse(BaseModel):
    id: str
    user_id: str
    cohort_key: str
    theta_proxy: float | None
    predicted_percentile: float | None
    band_low: float | None
    band_high: float | None
    status: str
    model_version: str
    computed_at: datetime

    class Config:
        from_attributes = True


class RankActivateRequest(BaseModel):
    cohort_key: str
    reason: str
    confirmation_phrase: str
    force: bool = False


class RankDeactivateRequest(BaseModel):
    reason: str
    confirmation_phrase: str


# --- GET /v1/admin/rank/status ---


@router.get("/admin/rank/status")
async def get_rank_status_endpoint(
    cohort_key: str | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Get rank status and latest run summary (admin only)."""
    require_admin(current_user)

    # Check runtime config
    runtime_cfg = await get_algo_runtime_config(db)
    rank_mode = await get_rank_mode(db, runtime_cfg)

    if rank_mode == "v0":
        raise HTTPException(
            status_code=403,
            detail="Rank is disabled (v0). Enable via runtime config override.",
        )

    # Get latest run
    stmt = select(RankModelRun).order_by(RankModelRun.created_at.desc())
    if cohort_key:
        stmt = stmt.where(RankModelRun.cohort_key == cohort_key)
    stmt = stmt.limit(1)

    result = await db.execute(stmt)
    latest_run = result.scalar_one_or_none()

    # Get snapshot stats
    stmt_snapshots = select(RankPredictionSnapshot)
    if cohort_key:
        stmt_snapshots = stmt_snapshots.where(RankPredictionSnapshot.cohort_key == cohort_key)

    result_snapshots = await db.execute(stmt_snapshots)
    snapshots = result_snapshots.scalars().all()

    ok_count = sum(1 for s in snapshots if s.status == RankSnapshotStatus.OK)
    total_count = len(snapshots)
    coverage = ok_count / total_count if total_count > 0 else 0.0

    return {
        "runtime": {
            "mode": rank_mode,
            "enabled_for_admin": await is_rank_enabled_for_admin(db, runtime_cfg),
            "frozen": runtime_cfg.safe_mode.get("freeze_updates", False),
        },
        "latest_run": {
            "id": str(latest_run.id) if latest_run else None,
            "cohort_key": latest_run.cohort_key if latest_run else None,
            "status": latest_run.status.value if latest_run else None,
            "created_at": latest_run.created_at.isoformat() if latest_run else None,
            "metrics": latest_run.metrics if latest_run else None,
        },
        "snapshots": {
            "total": total_count,
            "ok": ok_count,
            "coverage": coverage,
        },
    }


# --- POST /v1/admin/rank/runs ---


@router.post(
    "/admin/rank/runs",
    response_model=RankRunResponse,
    dependencies=[Depends(require_not_exam_mode("rank_run"))],
)
async def create_rank_run_endpoint(
    request: RankRunCreate,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Create and execute rank model run (admin only, shadow mode)."""
    require_admin(current_user)

    # Check runtime config
    runtime_cfg = await get_algo_runtime_config(db)
    rank_mode = await get_rank_mode(db, runtime_cfg)

    if rank_mode == "v0":
        raise HTTPException(
            status_code=403,
            detail="Rank is disabled (v0). Enable via runtime config override.",
        )

    # Check freeze mode
    if await is_safe_mode_freeze_updates(db):
        raise HTTPException(
            status_code=403,
            detail="Rank runs blocked: freeze_updates mode is enabled.",
        )

    # Create run
    run = RankModelRun(
        cohort_key=request.cohort_key,
        model_version="rank_v1_empirical_cdf",
        dataset_spec={},
        status=RankRunStatus.RUNNING,
        started_at=datetime.now(UTC),
        created_by_user_id=current_user.id,
    )
    db.add(run)
    await db.flush()

    try:
        # NOTE: Rank run execution is not yet implemented.
        # This endpoint creates a run record but does not execute the ranking algorithm.
        # To implement: call rank service with cohort_key, compute metrics, update run status.
        run.status = RankRunStatus.DONE
        run.finished_at = datetime.now(UTC)
        run.metrics = {
            "cohort_n": 0,
            "coverage": 0.0,
            "status": "not_implemented",
            "note": "Rank run execution not yet implemented",
        }

        await db.commit()
        await db.refresh(run)

        return RankRunResponse(
            id=str(run.id),
            cohort_key=run.cohort_key,
            model_version=run.model_version,
            status=run.status.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
            metrics=run.metrics,
            error=run.error,
            created_at=run.created_at,
        )
    except Exception as e:
        logger.exception("Rank run failed: %s", e)
        run.status = RankRunStatus.FAILED
        run.error = str(e)
        run.finished_at = datetime.now(UTC)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Rank run failed: {str(e)}")


# --- GET /v1/admin/rank/runs ---


@router.get("/admin/rank/runs", response_model=list[RankRunResponse])
async def list_rank_runs_endpoint(
    cohort_key: str | None = None,
    status: str | None = None,
    limit: int = 50,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """List rank model runs (admin only)."""
    require_admin(current_user)

    stmt = select(RankModelRun).order_by(RankModelRun.created_at.desc()).limit(limit)

    if cohort_key:
        stmt = stmt.where(RankModelRun.cohort_key == cohort_key)
    if status:
        stmt = stmt.where(RankModelRun.status == status)

    result = await db.execute(stmt)
    runs = result.scalars().all()

    return [
        RankRunResponse(
            id=str(r.id),
            cohort_key=r.cohort_key,
            model_version=r.model_version,
            status=r.status.value,
            started_at=r.started_at,
            finished_at=r.finished_at,
            metrics=r.metrics,
            error=r.error,
            created_at=r.created_at,
        )
        for r in runs
    ]


# --- GET /v1/admin/rank/snapshots ---


@router.get("/admin/rank/snapshots", response_model=list[RankSnapshotResponse])
async def list_rank_snapshots_endpoint(
    user_id: str | None = None,
    cohort_key: str | None = None,
    days: int = 30,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """List rank prediction snapshots (admin only)."""
    require_admin(current_user)

    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(days=days)

    stmt = (
        select(RankPredictionSnapshot)
        .where(RankPredictionSnapshot.computed_at >= cutoff)
        .order_by(RankPredictionSnapshot.computed_at.desc())
    )

    if user_id:
        stmt = stmt.where(RankPredictionSnapshot.user_id == UUID(user_id))
    if cohort_key:
        stmt = stmt.where(RankPredictionSnapshot.cohort_key == cohort_key)

    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    return [
        RankSnapshotResponse(
            id=str(s.id),
            user_id=str(s.user_id),
            cohort_key=s.cohort_key,
            theta_proxy=s.theta_proxy,
            predicted_percentile=s.predicted_percentile,
            band_low=s.band_low,
            band_high=s.band_high,
            status=s.status.value,
            model_version=s.model_version,
            computed_at=s.computed_at,
        )
        for s in snapshots
    ]


# --- POST /v1/admin/rank/activate ---


@router.post("/admin/rank/activate")
async def activate_rank_endpoint(
    request: RankActivateRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Activate rank for student-facing operations (admin only)."""
    require_admin(current_user)

    # Validate confirmation phrase
    if not request.confirmation_phrase or request.confirmation_phrase.strip().upper() != "ACTIVATE RANK":
        raise HTTPException(
            status_code=400,
            detail="confirmation_phrase is required and must be exactly 'ACTIVATE RANK'",
        )

    # Check eligibility
    from app.learning_engine.rank.eligibility import is_rank_eligible_for_activation

    eligible, reasons = await is_rank_eligible_for_activation(db, request.cohort_key)

    if not eligible and not request.force:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot activate: eligibility gates not passed. Reasons: {reasons}",
        )

    # Get current state
    runtime_cfg = await get_algo_runtime_config(db)
    current_rank_mode = await get_rank_mode(db, runtime_cfg)

    previous_state = {
        "rank_mode": current_rank_mode,
        "cohort_key": request.cohort_key,
    }

    # Update runtime config (set rank override to v1)
    from app.models.algo_runtime import AlgoRuntimeConfig

    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=500, detail="Runtime config not found")

    config.config_json = config.config_json or {}
    config.config_json["overrides"] = config.config_json.get("overrides", {})
    config.config_json["overrides"][MODULE_RANK] = "v1"
    config.changed_by_user_id = current_user.id
    await db.commit()

    new_state = {
        "rank_mode": "v1",
        "cohort_key": request.cohort_key,
    }

    # Create audit event
    event = RankActivationEvent(
        previous_state=previous_state,
        new_state={**new_state, "details": {"confirmation_phrase_provided": True}},
        reason=request.reason,
        confirmation_phrase=request.confirmation_phrase,
        created_by_user_id=current_user.id,
    )
    db.add(event)
    await db.commit()

    return {"message": "Rank activated successfully", "state": new_state}


# --- POST /v1/admin/rank/deactivate ---


@router.post("/admin/rank/deactivate")
async def deactivate_rank_endpoint(
    request: RankDeactivateRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Deactivate rank (kill-switch, admin only)."""
    require_admin(current_user)

    # Validate confirmation phrase
    if not request.confirmation_phrase or request.confirmation_phrase.strip().upper() != "DEACTIVATE RANK":
        raise HTTPException(
            status_code=400,
            detail="confirmation_phrase is required and must be exactly 'DEACTIVATE RANK'",
        )

    # Get current state
    runtime_cfg = await get_algo_runtime_config(db)
    current_rank_mode = await get_rank_mode(db, runtime_cfg)

    previous_state = {
        "rank_mode": current_rank_mode,
    }

    # Update runtime config (set rank override to v0)
    from app.models.algo_runtime import AlgoRuntimeConfig

    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=500, detail="Runtime config not found")

    config.config_json = config.config_json or {}
    config.config_json["overrides"] = config.config_json.get("overrides", {})
    config.config_json["overrides"][MODULE_RANK] = "v0"
    config.changed_by_user_id = current_user.id
    await db.commit()

    new_state = {
        "rank_mode": "v0",
    }

    # Create audit event
    event = RankActivationEvent(
        previous_state=previous_state,
        new_state={**new_state, "details": {"confirmation_phrase_provided": True}},
        reason=request.reason,
        confirmation_phrase=request.confirmation_phrase,
        created_by_user_id=current_user.id,
    )
    db.add(event)
    await db.commit()

    return {"message": "Rank deactivated successfully", "state": new_state}
