"""Admin warehouse export endpoints."""

import logging
from datetime import date, datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.logging import get_logger
from app.models.algo_runtime import AlgoRuntimeConfig, AlgoSwitchEvent
from app.security.exam_mode_gate import require_not_exam_mode
from app.models.user import User
from app.models.warehouse import (
    WarehouseExportDataset,
    WarehouseExportRun,
    WarehouseExportRunStatus,
    WarehouseExportRunType,
    WarehouseExportState,
)
from app.warehouse.exporter import (
    _get_warehouse_mode,
    run_backfill,
    run_incremental_exports,
    start_export,
)

logger = get_logger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


# Police mode confirmation phrases
WAREHOUSE_PHRASES = {
    "disabled": "SWITCH WAREHOUSE TO DISABLED",
    "shadow": "SWITCH WAREHOUSE TO SHADOW",
    "active": "SWITCH WAREHOUSE TO ACTIVE",
}

EXPORT_PHRASES = {
    "export": "RUN WAREHOUSE EXPORT",
    "backfill": "RUN WAREHOUSE BACKFILL",
}


class WarehouseRuntimeStatus(BaseModel):
    """Warehouse runtime status response."""

    requested_mode: str
    effective_mode: str
    warehouse_freeze: bool
    readiness: dict[str, Any] | None = None
    last_export_run: dict[str, Any] | None = None
    last_transform_run: dict[str, Any] | None = None
    warnings: list[str] = []
    last_export_runs: list[dict[str, Any]]


class WarehouseSwitchRequest(BaseModel):
    """Request to switch warehouse mode."""

    mode: str = Field(..., description="Target mode: disabled, shadow, or active")
    reason: str = Field(..., min_length=10, description="Reason for switch (min 10 chars)")
    confirmation_phrase: str = Field(..., description="Confirmation phrase")


class ExportRunRequest(BaseModel):
    """Request to run an export."""

    dataset: str = Field(..., description="Dataset to export")
    run_type: str = Field(..., description="Run type: incremental, backfill, or full_rebuild")
    range_start: datetime | date | None = Field(default=None, description="Range start (optional)")
    range_end: datetime | date | None = Field(default=None, description="Range end (optional)")
    reason: str = Field(..., min_length=10, description="Reason for export (min 10 chars)")
    confirmation_phrase: str = Field(..., description="Confirmation phrase")


class BackfillRequest(BaseModel):
    """Request to run a backfill."""

    dataset: str = Field(..., description="Dataset to export")
    range_start: datetime | date = Field(..., description="Range start")
    range_end: datetime | date = Field(..., description="Range end")
    reason: str = Field(..., min_length=10, description="Reason for backfill (min 10 chars)")
    confirmation_phrase: str = Field(..., description="Confirmation phrase")


@router.get("/admin/warehouse/runtime", response_model=WarehouseRuntimeStatus)
async def get_warehouse_runtime(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get warehouse runtime configuration (admin only).

    Returns requested mode, effective mode, freeze status, readiness, and recent export runs.
    """
    require_admin(current_user)

    from app.warehouse.exporter import get_effective_warehouse_mode
    from app.warehouse.readiness import evaluate_warehouse_readiness

    requested_mode, warehouse_freeze = _get_warehouse_mode(db)
    effective_mode, warnings = get_effective_warehouse_mode(db)
    readiness = evaluate_warehouse_readiness(db)

    # Get last successful export run
    last_export_run = (
        db.query(WarehouseExportRun)
        .filter(
            WarehouseExportRun.status.in_(
                [WarehouseExportRunStatus.DONE, WarehouseExportRunStatus.SHADOW_DONE_FILES_ONLY]
            )
        )
        .order_by(WarehouseExportRun.finished_at.desc())
        .first()
    )

    # Get last successful transform run
    # NOTE: snowflake_transform_run table is not yet implemented.
    # When implemented, uncomment the query below to fetch the last transform run.
    last_transform_run = None
    # last_transform_run = (
    #     db.query(SnowflakeTransformRun)
    #     .filter(SnowflakeTransformRun.status == SnowflakeTransformRunStatus.DONE)
    #     .order_by(SnowflakeTransformRun.finished_at.desc())
    #     .first()
    # )

    # Get last 10 export runs
    last_runs = (
        db.query(WarehouseExportRun)
        .order_by(WarehouseExportRun.created_at.desc())
        .limit(10)
        .all()
    )

    return WarehouseRuntimeStatus(
        requested_mode=requested_mode,
        effective_mode=effective_mode,
        warehouse_freeze=warehouse_freeze,
        readiness=readiness.to_dict() if readiness else None,
        last_export_run={
            "run_id": str(last_export_run.run_id),
            "dataset": last_export_run.dataset.value,
            "run_type": last_export_run.run_type.value,
            "status": last_export_run.status.value,
            "finished_at": last_export_run.finished_at.isoformat() if last_export_run.finished_at else None,
        } if last_export_run else None,
        last_transform_run=last_transform_run,
        warnings=warnings,
        last_export_runs=[
            {
                "run_id": str(run.run_id),
                "dataset": run.dataset.value,
                "run_type": run.run_type.value,
                "status": run.status.value,
                "rows_exported": run.rows_exported,
                "files_written": run.files_written,
                "created_at": run.created_at.isoformat() if run.created_at else None,
            }
            for run in last_runs
        ],
    )


@router.post("/admin/warehouse/runtime/switch", response_model=WarehouseRuntimeStatus)
async def switch_warehouse_runtime(
    request: WarehouseSwitchRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Switch warehouse runtime mode (admin only, police mode required).
    """
    require_admin(current_user)

    # Validate mode
    if request.mode not in ["disabled", "shadow", "active"]:
        raise HTTPException(status_code=400, detail="Invalid mode: must be disabled, shadow, or active")

    # Check two-person approval requirement for enabling Snowflake export in production
    if request.mode == "active":
        from app.api.v1.endpoints.admin_approvals import (
            check_approval_required_or_raise,
            requires_two_person_approval,
        )
        
        if requires_two_person_approval("SNOWFLAKE_EXPORT_ENABLE"):
            check_approval_required_or_raise(db, "SNOWFLAKE_EXPORT_ENABLE", current_user, http_request)

    # Validate confirmation phrase
    expected_phrase = WAREHOUSE_PHRASES.get(request.mode)
    if request.confirmation_phrase != expected_phrase:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid confirmation phrase. Expected: {expected_phrase}",
        )

    # Get current config
    config = db.query(AlgoRuntimeConfig).order_by(AlgoRuntimeConfig.updated_at.desc()).first()
    if not config:
        raise HTTPException(status_code=500, detail="Runtime config not found")

    config_json = config.config_json or {}
    previous_mode = config_json.get("warehouse_mode", "disabled")

    # Update config
    config_json["warehouse_mode"] = request.mode
    config.config_json = config_json
    config.changed_by_user_id = current_user.id
    config.reason = request.reason
    config.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Log audit event
    switch_event = AlgoSwitchEvent(
        previous_config={"warehouse_mode": previous_mode},
        new_config={"warehouse_mode": request.mode},
        reason=request.reason,
        created_by_user_id=current_user.id,
    )
    db.add(switch_event)
    db.commit()

    logger.info(
        f"Warehouse mode switched from {previous_mode} to {request.mode} by {current_user.id}: {request.reason}"
    )

    return await get_warehouse_runtime(current_user, db)


@router.get("/admin/warehouse/runs")
async def get_warehouse_runs(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of runs to return"),
    dataset: str | None = Query(None, description="Filter by dataset"),
    status: str | None = Query(None, description="Filter by status"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get warehouse export runs (admin only).
    """
    require_admin(current_user)

    query = db.query(WarehouseExportRun)

    if dataset:
        query = query.filter(WarehouseExportRun.dataset == WarehouseExportDataset(dataset))
    if status:
        query = query.filter(WarehouseExportRun.status == WarehouseExportRunStatus(status))

    runs = query.order_by(WarehouseExportRun.created_at.desc()).limit(limit).all()

    return [
        {
            "run_id": str(run.run_id),
            "run_type": run.run_type.value,
            "dataset": run.dataset.value,
            "status": run.status.value,
            "range_start": run.range_start.isoformat() if run.range_start else None,
            "range_end": run.range_end.isoformat() if run.range_end else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "rows_exported": run.rows_exported,
            "files_written": run.files_written,
            "manifest_path": run.manifest_path,
            "last_error": run.last_error,
            "details": run.details,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }
        for run in runs
    ]


@router.post(
    "/admin/warehouse/export/run",
    dependencies=[Depends(require_not_exam_mode("warehouse_export"))],
)
async def run_warehouse_export(
    request: ExportRunRequest,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Run a manual warehouse export (admin only, police mode required).
    """
    require_admin(current_user)

    # Validate confirmation phrase
    if request.run_type == "backfill":
        expected_phrase = EXPORT_PHRASES["backfill"]
    else:
        expected_phrase = EXPORT_PHRASES["export"]

    if request.confirmation_phrase != expected_phrase:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid confirmation phrase. Expected: {expected_phrase}",
        )

    # Validate dataset
    try:
        WarehouseExportDataset(request.dataset)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid dataset: {request.dataset}")

    # Validate run_type
    try:
        WarehouseExportRunType(request.run_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid run_type: {request.run_type}")

    run_id = start_export(
        db,
        request.dataset,
        request.run_type,
        request.range_start,
        request.range_end,
        current_user.id,
        request.reason,
    )

    return {"run_id": str(run_id), "status": "started"}


@router.post(
    "/admin/warehouse/export/incremental",
    dependencies=[Depends(require_not_exam_mode("warehouse_incremental_export"))],
)
async def run_incremental_warehouse_export(
    reason: str = Query(..., min_length=10, description="Reason for export"),
    confirmation_phrase: str = Query(..., description="Confirmation phrase"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Run incremental warehouse exports for all datasets (admin only, police mode required).
    """
    require_admin(current_user)

    # Validate confirmation phrase
    if confirmation_phrase != EXPORT_PHRASES["export"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid confirmation phrase. Expected: {EXPORT_PHRASES['export']}",
        )

    run_ids = run_incremental_exports(db, current_user.id, reason)

    return {"run_ids": [str(rid) for rid in run_ids], "status": "started"}


@router.post(
    "/admin/warehouse/export/backfill",
    dependencies=[Depends(require_not_exam_mode("warehouse_backfill"))],
)
async def run_warehouse_backfill(
    request: BackfillRequest,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Run a warehouse backfill export (admin only, police mode required).
    """
    require_admin(current_user)

    # Validate confirmation phrase
    if request.confirmation_phrase != EXPORT_PHRASES["backfill"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid confirmation phrase. Expected: {EXPORT_PHRASES['backfill']}",
        )

    # Validate dataset
    try:
        WarehouseExportDataset(request.dataset)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid dataset: {request.dataset}")

    run_id = run_backfill(
        db,
        request.dataset,
        request.range_start,
        request.range_end,
        current_user.id,
        request.reason,
    )

    return {"run_id": str(run_id), "status": "started"}
