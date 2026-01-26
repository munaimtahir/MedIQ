"""Admin endpoints for Neo4j concept graph (shadow infrastructure)."""

import logging
from datetime import datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.config import settings
from app.graph.concept_sync import run_full_rebuild, run_incremental_sync
from app.security.exam_mode_gate import require_not_exam_mode
from app.graph.health import get_graph_health
from app.graph.neo4j_client import ping
from app.graph.readiness import evaluate_graph_readiness
from app.models.algo_runtime import AlgoRuntimeConfig, AlgoSwitchEvent
from app.models.neo4j_sync import Neo4jSyncRun, Neo4jSyncRunStatus, Neo4jSyncRunType
from app.models.user import User
from app.api.v1.endpoints.admin_algorithms_validation import validate_confirmation_phrase

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


def require_admin_or_reviewer(user: User) -> None:
    """Require user to be ADMIN or REVIEWER."""
    if user.role not in ("ADMIN", "REVIEWER"):
        raise HTTPException(status_code=403, detail="Admin or Reviewer access required")


class GraphHealthResponse(BaseModel):
    """Graph health response model."""

    enabled: bool
    reachable: bool
    latency_ms: int | None
    database: str
    schema_ok: bool
    node_count: int | None
    edge_count: int | None


@router.get("/admin/graph/health", response_model=GraphHealthResponse)
async def get_graph_health_endpoint(
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Get Neo4j concept graph health status (admin/reviewer only).

    Returns health information including:
    - enabled: Whether Neo4j is enabled
    - reachable: Whether Neo4j is reachable
    - latency_ms: Ping latency in milliseconds
    - database: Database name
    - schema_ok: Whether constraints and indexes are present
    - node_count: Number of Concept nodes
    - edge_count: Number of PREREQ edges

    Fails open: If Neo4j is disabled or down, returns safe defaults without crashing.
    """
    require_admin_or_reviewer(current_user)

    try:
        health_info = get_graph_health()
        logger.debug(
            f"Graph health check: enabled={health_info['enabled']}, "
            f"reachable={health_info.get('reachable', False)}"
        )
        return GraphHealthResponse(**health_info)
    except Exception as e:
        logger.error(f"Unexpected error in graph health endpoint: {e}", exc_info=True)
        # Fail open - return safe response
        return GraphHealthResponse(
            enabled=False,
            reachable=False,
            latency_ms=None,
            database="neo4j",
            schema_ok=False,
            node_count=None,
            edge_count=None,
        )


class SyncRunResponse(BaseModel):
    """Sync run response model."""

    id: str
    run_type: str
    status: str
    started_at: str | None
    finished_at: str | None
    nodes_upserted: int
    edges_upserted: int
    nodes_inactivated: int
    edges_inactivated: int
    cycle_detected: bool
    last_error: str | None
    details: dict[str, Any] | None
    created_at: str


class IncrementalSyncRequest(BaseModel):
    """Request to run incremental sync."""

    reason: str | None = None
    confirmation_phrase: str | None = None


class FullRebuildRequest(BaseModel):
    """Request to run full rebuild."""

    reason: str
    confirmation_phrase: str


@router.get("/admin/graph/runs")
async def get_graph_sync_runs(
    days: int = Query(30, ge=1, le=365),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get Neo4j sync run history (admin/reviewer only).

    Args:
        days: Number of days to look back (default 30, max 365)
    """
    require_admin_or_reviewer(current_user)

    cutoff = datetime.utcnow() - timedelta(days=days)
    runs = (
        db.query(Neo4jSyncRun)
        .filter(Neo4jSyncRun.created_at >= cutoff)
        .order_by(desc(Neo4jSyncRun.created_at))
        .limit(100)
        .all()
    )

    return {
        "runs": [
            {
                "id": str(run.id),
                "run_type": run.run_type.value,
                "status": run.status.value,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "nodes_upserted": run.nodes_upserted,
                "edges_upserted": run.edges_upserted,
                "nodes_inactivated": run.nodes_inactivated,
                "edges_inactivated": run.edges_inactivated,
                "cycle_detected": run.cycle_detected,
                "last_error": run.last_error,
                "details": run.details,
                "created_at": run.created_at.isoformat(),
            }
            for run in runs
        ]
    }


@router.post(
    "/admin/graph/sync/incremental",
    dependencies=[Depends(require_not_exam_mode("graph_incremental_sync"))],
)
async def trigger_incremental_sync(
    request: IncrementalSyncRequest,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Manually trigger incremental sync (admin only).

    Args:
        request: Optional reason and confirmation phrase

    Returns:
        Sync run ID and status
    """
    require_admin(current_user)

    # Optional confirmation (recommended but not required)
    if request.confirmation_phrase:
        if request.confirmation_phrase != "RUN GRAPH SYNC":
            raise HTTPException(
                status_code=400,
                detail="Invalid confirmation phrase. Must be exactly 'RUN GRAPH SYNC'",
            )

    if request.reason and len(request.reason.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Reason must be at least 10 characters if provided",
        )

    logger.info(f"Incremental sync triggered by {current_user.email}. Reason: {request.reason or 'none'}")

    try:
        run_id = run_incremental_sync(db, actor_user_id=current_user.id)
        run = db.query(Neo4jSyncRun).filter(Neo4jSyncRun.id == run_id).first()

        return {
            "run_id": str(run_id),
            "status": run.status.value if run else "queued",
            "message": "Incremental sync started",
        }
    except Exception as e:
        logger.error(f"Error triggering incremental sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post(
    "/admin/graph/sync/full",
    dependencies=[Depends(require_not_exam_mode("graph_full_sync"))],
)
async def trigger_full_rebuild(
    request: FullRebuildRequest,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Manually trigger full rebuild (admin only, requires police mode).

    Args:
        request: Reason and confirmation phrase (required)

    Returns:
        Sync run ID and status
    """
    require_admin(current_user)

    # Police mode check
    if request.confirmation_phrase != "RUN GRAPH FULL REBUILD":
        raise HTTPException(
            status_code=400,
            detail="Invalid confirmation phrase. Must be exactly 'RUN GRAPH FULL REBUILD'",
        )

    if not request.reason or len(request.reason.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Reason is required and must be at least 10 characters",
        )

    logger.warning(f"Full rebuild triggered by {current_user.email}. Reason: {request.reason}")

    try:
        run_id = run_full_rebuild(db, actor_user_id=current_user.id)
        run = db.query(Neo4jSyncRun).filter(Neo4jSyncRun.id == run_id).first()

        return {
            "run_id": str(run_id),
            "status": run.status.value if run else "queued",
            "message": "Full rebuild started",
        }
    except Exception as e:
        logger.error(f"Error triggering full rebuild: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {str(e)}")


# ============================================================================
# Graph Runtime Configuration
# ============================================================================


class ReadinessCheckDetails(BaseModel):
    """Details for a single readiness check."""

    ok: bool
    details: dict[str, Any]


class ReadinessStatus(BaseModel):
    """Graph readiness status."""

    ready: bool
    blocking_reasons: list[str]
    checks: dict[str, ReadinessCheckDetails]


class GraphRuntimeStatus(BaseModel):
    """Graph runtime status response."""

    requested_mode: str  # "disabled" | "shadow" | "active"
    effective_mode: str  # "disabled" | "shadow" | "active" (may downgrade)
    neo4j_enabled_env: bool
    reachable: bool
    readiness: ReadinessStatus | None = None  # Only present if requested_mode != "disabled"
    last_sync: dict[str, Any] | None = None


class GraphSwitchRequest(BaseModel):
    """Request to switch graph mode."""

    mode: str  # "disabled" | "shadow" | "active"
    reason: str
    confirmation_phrase: str


def get_graph_runtime_mode(db: Session) -> str:
    """
    Get current graph mode from runtime config.

    Returns:
        "disabled", "shadow", or "active" (defaults to "disabled")
    """
    config = db.query(AlgoRuntimeConfig).first()

    if not config:
        return "disabled"

    config_json = config.config_json or {}
    return config_json.get("graph_mode", "disabled")


def get_effective_graph_mode(db: Session, requested_mode: str) -> str:
    """
    Get effective graph mode (may downgrade from requested based on readiness).

    Rules:
    - requested disabled => effective disabled
    - requested shadow => effective shadow ONLY if readiness passes; else disabled
    - requested active => effective active ONLY if readiness passes AND FEATURE_GRAPH_ACTIVE=true; else shadow or disabled
    """
    if requested_mode == "disabled":
        return "disabled"

    # Evaluate readiness
    readiness = evaluate_graph_readiness(db)

    if requested_mode == "shadow":
        return "shadow" if readiness.ready else "disabled"

    if requested_mode == "active":
        if not settings.FEATURE_GRAPH_ACTIVE:
            return "shadow"  # Feature flag blocks active mode
        return "active" if readiness.ready else "shadow"

    # Fallback
    return "disabled"


@router.get("/admin/graph/runtime", response_model=GraphRuntimeStatus)
async def get_graph_runtime(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get graph runtime configuration (admin/reviewer only).

    Returns requested mode, effective mode, Neo4j reachability, readiness, and last sync info.
    """
    require_admin_or_reviewer(current_user)

    requested_mode = get_graph_runtime_mode(db)
    effective_mode = get_effective_graph_mode(db, requested_mode)

    # Get Neo4j status
    neo4j_enabled = settings.NEO4J_ENABLED
    is_reachable, latency_ms, ping_details = ping()

    # Get readiness (only if not disabled)
    readiness = None
    if requested_mode != "disabled":
        readiness_result = evaluate_graph_readiness(db)
        readiness = ReadinessStatus(
            ready=readiness_result.ready,
            blocking_reasons=readiness_result.blocking_reasons,
            checks={
                name: ReadinessCheckDetails(ok=check.ok, details=check.details)
                for name, check in readiness_result.checks.items()
            },
        )

    # Get last sync run
    last_sync = None
    last_run = (
        db.query(Neo4jSyncRun)
        .filter(
            Neo4jSyncRun.status == Neo4jSyncRunStatus.DONE,
            Neo4jSyncRun.run_type.in_([Neo4jSyncRunType.INCREMENTAL, Neo4jSyncRunType.FULL]),
        )
        .order_by(Neo4jSyncRun.finished_at.desc())
        .first()
    )
    if last_run:
        last_sync = {
            "run_id": str(last_run.id),
            "run_type": last_run.run_type.value,
            "finished_at": last_run.finished_at.isoformat() if last_run.finished_at else None,
            "nodes_upserted": last_run.nodes_upserted,
            "edges_upserted": last_run.edges_upserted,
            "cycle_detected": last_run.cycle_detected,
        }

    # Note: Last switch event can be queried from algo_switch_event table
    # but we don't include it in response for now (can add if needed)

    return GraphRuntimeStatus(
        requested_mode=requested_mode,
        effective_mode=effective_mode,
        neo4j_enabled_env=neo4j_enabled,
        reachable=is_reachable,
        readiness=readiness,
        last_sync=last_sync,
    )


@router.post("/admin/graph/runtime/switch")
async def switch_graph_runtime(
    request: GraphSwitchRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Switch graph runtime mode (admin only, requires police mode).

    Args:
        request: Mode, reason, and confirmation phrase

    Returns:
        Updated runtime status
    """
    require_admin(current_user)

    # Validate mode
    valid_modes = ["disabled", "shadow", "active"]
    if request.mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be one of: {', '.join(valid_modes)}",
        )

    # Check two-person approval requirement for enabling Neo4j in production
    if request.mode in ("shadow", "active"):
        from app.api.v1.endpoints.admin_approvals import (
            check_approval_required_or_raise,
            requires_two_person_approval,
        )
        
        if requires_two_person_approval("NEO4J_ENABLE"):
            check_approval_required_or_raise(db, "NEO4J_ENABLE", current_user, http_request)

    # Validate confirmation phrase
    expected_phrases = {
        "disabled": "SWITCH GRAPH TO DISABLED",
        "shadow": "SWITCH GRAPH TO SHADOW",
        "active": "SWITCH GRAPH TO ACTIVE",
    }
    expected_phrase = expected_phrases[request.mode]
    if request.confirmation_phrase != expected_phrase:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid confirmation phrase. Must be exactly '{expected_phrase}'",
        )

    # Validate reason
    if not request.reason or len(request.reason.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Reason is required and must be at least 10 characters",
        )

    # Check feature flag for active mode
    if request.mode == "active" and not settings.FEATURE_GRAPH_ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Active mode is not enabled (FEATURE_GRAPH_ACTIVE=false)",
        )

    # Get or create runtime config
    config = db.query(AlgoRuntimeConfig).first()
    if not config:
        from app.models.algo_runtime import AlgoRuntimeProfile

        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={
                "profile": "V1_PRIMARY",
                "overrides": {},
                "safe_mode": {"freeze_updates": False, "prefer_cache": True},
                "graph_mode": "disabled",
            },
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    # Update config
    config_json = config.config_json or {}
    old_mode = config_json.get("graph_mode", "disabled")
    config_json["graph_mode"] = request.mode
    config.config_json = config_json
    config.changed_by_user_id = current_user.id
    config.reason = request.reason

    # Create audit event
    switch_event = AlgoSwitchEvent(
        previous_config={"graph_mode": old_mode},
        new_config={"graph_mode": request.mode},
        reason=request.reason,
        created_by_user_id=current_user.id,
    )
    db.add(switch_event)

    db.commit()

    logger.warning(
        f"Graph mode switched from {old_mode} to {request.mode} by {current_user.email}. Reason: {request.reason}"
    )

    # Return updated status
    return await get_graph_runtime(current_user=current_user, db=db)

