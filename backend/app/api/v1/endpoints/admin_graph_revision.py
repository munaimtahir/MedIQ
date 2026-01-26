"""Graph revision admin API — shadow-first module for prerequisite-aware planning."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.graph.neo4j_client import detect_cycles, get_graph_stats, is_neo4j_available
from app.security.exam_mode_gate import require_not_exam_mode
from app.graph.sync import sync_prereq_edges_to_neo4j
from app.learning_engine.graph_revision.planner import get_planner_config
from app.learning_engine.runtime import (
    MODULE_GRAPH_REVISION,
    get_algo_runtime_config,
    get_graph_revision_mode,
    is_graph_revision_active_allowed,
    is_safe_mode_freeze_updates,
)
from app.models.algo_runtime import AlgoRuntimeConfig
from app.models.graph_revision import (
    GraphRevisionActivationEvent,
    GraphRevisionConfig,
    GraphRevisionRun,
    GraphRevisionRunStatus,
    PrereqEdge,
    PrereqSyncRun,
    PrereqSyncStatus,
    ShadowRevisionPlan,
)
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


# --- Schemas ---


class PrereqEdgeCreate(BaseModel):
    from_theme_id: int
    to_theme_id: int
    weight: float = 1.0
    source: str = "manual"
    confidence: float | None = None


class PrereqEdgeUpdate(BaseModel):
    weight: float | None = None
    source: str | None = None
    confidence: float | None = None
    is_active: bool | None = None


class PrereqEdgeResponse(BaseModel):
    id: str
    from_theme_id: int
    to_theme_id: int
    weight: float
    source: str
    confidence: float | None
    is_active: bool
    created_by_user_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PrereqSyncRunResponse(BaseModel):
    id: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    details_json: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True


class ShadowPlanResponse(BaseModel):
    id: str
    user_id: str
    run_date: date
    mode: str
    baseline_count: int
    injected_count: int
    plan_json: list[dict[str, Any]]
    computed_at: datetime

    class Config:
        from_attributes = True


class GraphRevisionActivateRequest(BaseModel):
    reason: str
    confirmation_phrase: str
    force: bool = False


class GraphRevisionDeactivateRequest(BaseModel):
    reason: str
    confirmation_phrase: str


# --- POST /v1/admin/graph-revision/sync ---


@router.post(
    "/admin/graph-revision/sync",
    response_model=PrereqSyncRunResponse,
    dependencies=[Depends(require_not_exam_mode("graph_revision_sync"))],
)
async def sync_neo4j_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Trigger Neo4j sync from Postgres prereq_edges (admin only)."""
    require_admin(current_user)

    sync_run = await sync_prereq_edges_to_neo4j(db, created_by_user_id=current_user.id)

    return PrereqSyncRunResponse(
        id=str(sync_run.id),
        status=sync_run.status.value,
        started_at=sync_run.started_at,
        finished_at=sync_run.finished_at,
        details_json=sync_run.details_json,
        created_at=sync_run.created_at,
    )


# --- GET /v1/admin/graph-revision/sync/runs ---


@router.get("/admin/graph-revision/sync/runs", response_model=list[PrereqSyncRunResponse])
async def list_sync_runs_endpoint(
    limit: int = 50,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """List Neo4j sync runs (admin only)."""
    require_admin(current_user)

    stmt = select(PrereqSyncRun).order_by(PrereqSyncRun.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    runs = result.scalars().all()

    return [
        PrereqSyncRunResponse(
            id=str(r.id),
            status=r.status.value,
            started_at=r.started_at,
            finished_at=r.finished_at,
            details_json=r.details_json,
            created_at=r.created_at,
        )
        for r in runs
    ]


# --- GET /v1/admin/graph-revision/sync/runs/{id} ---


@router.get("/admin/graph-revision/sync/runs/{run_id}", response_model=PrereqSyncRunResponse)
async def get_sync_run_endpoint(
    run_id: str,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Get Neo4j sync run details (admin only)."""
    require_admin(current_user)

    stmt = select(PrereqSyncRun).where(PrereqSyncRun.id == UUID(run_id))
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found")

    return PrereqSyncRunResponse(
        id=str(run.id),
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        details_json=run.details_json,
        created_at=run.created_at,
    )


# --- GET /v1/admin/graph-revision/health ---


@router.get("/admin/graph-revision/health")
async def get_health_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Get Neo4j health status and graph statistics (admin only)."""
    require_admin(current_user)

    available = is_neo4j_available()
    stats = get_graph_stats()
    cycle_report = detect_cycles()

    # Get last sync run
    stmt = select(PrereqSyncRun).order_by(PrereqSyncRun.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    last_sync = result.scalar_one_or_none()

    return {
        "neo4j_available": available,
        "graph_stats": stats,
        "cycle_check": cycle_report,
        "last_sync": {
            "id": str(last_sync.id) if last_sync else None,
            "status": last_sync.status.value if last_sync else None,
            "finished_at": last_sync.finished_at.isoformat() if last_sync and last_sync.finished_at else None,
            "details": last_sync.details_json if last_sync else None,
        },
    }


# --- GET /v1/admin/graph-revision/run-metrics ---


@router.get("/admin/graph-revision/run-metrics")
async def get_run_metrics_endpoint(
    days: int = 30,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Get graph revision run metrics (admin only)."""
    require_admin(current_user)

    from app.models.graph_revision import GraphRevisionRun

    cutoff = date.today() - timedelta(days=days)
    stmt = (
        select(GraphRevisionRun)
        .where(GraphRevisionRun.run_date >= cutoff)
        .order_by(GraphRevisionRun.created_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()

    return {
        "runs": [
            {
                "id": str(r.id),
                "run_date": r.run_date.isoformat(),
                "mode": r.mode,
                "metrics": r.metrics,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
            }
            for r in runs
        ],
    }


# --- GET /v1/admin/graph-revision/edges ---


@router.get("/admin/graph-revision/edges", response_model=list[PrereqEdgeResponse])
async def list_edges_endpoint(
    from_theme_id: int | None = None,
    to_theme_id: int | None = None,
    is_active: bool | None = None,
    limit: int = 100,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """List prerequisite edges (admin only)."""
    require_admin(current_user)

    stmt = select(PrereqEdge).limit(limit)

    if from_theme_id:
        stmt = stmt.where(PrereqEdge.from_theme_id == from_theme_id)
    if to_theme_id:
        stmt = stmt.where(PrereqEdge.to_theme_id == to_theme_id)
    if is_active is not None:
        stmt = stmt.where(PrereqEdge.is_active == is_active)

    result = await db.execute(stmt)
    edges = result.scalars().all()

    return [
        PrereqEdgeResponse(
            id=str(e.id),
            from_theme_id=e.from_theme_id,
            to_theme_id=e.to_theme_id,
            weight=e.weight,
            source=e.source,
            confidence=e.confidence,
            is_active=e.is_active,
            created_by_user_id=str(e.created_by_user_id) if e.created_by_user_id else None,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in edges
    ]


# --- POST /v1/admin/graph-revision/edges ---


@router.post("/admin/graph-revision/edges", response_model=PrereqEdgeResponse)
async def create_edge_endpoint(
    request: PrereqEdgeCreate,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Create prerequisite edge (admin only)."""
    require_admin(current_user)

    # Check if edge already exists (active)
    stmt = select(PrereqEdge).where(
        PrereqEdge.from_theme_id == request.from_theme_id,
        PrereqEdge.to_theme_id == request.to_theme_id,
        PrereqEdge.is_active == True,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="Active edge already exists")

    edge = PrereqEdge(
        from_theme_id=request.from_theme_id,
        to_theme_id=request.to_theme_id,
        weight=request.weight,
        source=request.source,
        confidence=request.confidence,
        is_active=True,
        created_by_user_id=current_user.id,
    )

    db.add(edge)
    await db.commit()
    await db.refresh(edge)

    return PrereqEdgeResponse(
        id=str(edge.id),
        from_theme_id=edge.from_theme_id,
        to_theme_id=edge.to_theme_id,
        weight=edge.weight,
        source=edge.source,
        confidence=edge.confidence,
        is_active=edge.is_active,
        created_by_user_id=str(edge.created_by_user_id) if edge.created_by_user_id else None,
        created_at=edge.created_at,
        updated_at=edge.updated_at,
    )


# --- PUT /v1/admin/graph-revision/edges/{id} ---


@router.put("/admin/graph-revision/edges/{edge_id}", response_model=PrereqEdgeResponse)
async def update_edge_endpoint(
    edge_id: str,
    request: PrereqEdgeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Update prerequisite edge (admin only)."""
    require_admin(current_user)

    stmt = select(PrereqEdge).where(PrereqEdge.id == UUID(edge_id))
    result = await db.execute(stmt)
    edge = result.scalar_one_or_none()

    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")

    if request.weight is not None:
        edge.weight = request.weight
    if request.source is not None:
        edge.source = request.source
    if request.confidence is not None:
        edge.confidence = request.confidence
    if request.is_active is not None:
        edge.is_active = request.is_active

    await db.commit()
    await db.refresh(edge)

    return PrereqEdgeResponse(
        id=str(edge.id),
        from_theme_id=edge.from_theme_id,
        to_theme_id=edge.to_theme_id,
        weight=edge.weight,
        source=edge.source,
        confidence=edge.confidence,
        is_active=edge.is_active,
        created_by_user_id=str(edge.created_by_user_id) if edge.created_by_user_id else None,
        created_at=edge.created_at,
        updated_at=edge.updated_at,
    )


# --- DELETE /v1/admin/graph-revision/edges/{id} ---


@router.delete("/admin/graph-revision/edges/{edge_id}")
async def delete_edge_endpoint(
    edge_id: str,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Soft delete prerequisite edge (admin only)."""
    require_admin(current_user)

    stmt = select(PrereqEdge).where(PrereqEdge.id == UUID(edge_id))
    result = await db.execute(stmt)
    edge = result.scalar_one_or_none()

    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")

    edge.is_active = False
    await db.commit()

    return {"message": "Edge deactivated"}


# --- GET /v1/admin/graph-revision/shadow-plans ---


@router.get("/admin/graph-revision/shadow-plans", response_model=list[ShadowPlanResponse])
async def list_shadow_plans_endpoint(
    user_id: str | None = None,
    days: int = 7,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """List shadow revision plans (admin only)."""
    require_admin(current_user)

    cutoff_date = date.today() - timedelta(days=days)

    stmt = (
        select(ShadowRevisionPlan)
        .where(ShadowRevisionPlan.run_date >= cutoff_date)
        .order_by(ShadowRevisionPlan.computed_at.desc())
    )

    if user_id:
        stmt = stmt.where(ShadowRevisionPlan.user_id == UUID(user_id))

    result = await db.execute(stmt)
    plans = result.scalars().all()

    return [
        ShadowPlanResponse(
            id=str(p.id),
            user_id=str(p.user_id),
            run_date=p.run_date,
            mode=p.mode,
            baseline_count=p.baseline_count,
            injected_count=p.injected_count,
            plan_json=p.plan_json,
            computed_at=p.computed_at,
        )
        for p in plans
    ]


# --- POST /v1/admin/graph-revision/activate ---


@router.post("/admin/graph-revision/activate")
async def activate_graph_revision_endpoint(
    request: GraphRevisionActivateRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Activate graph revision for student-facing operations (admin only)."""
    require_admin(current_user)

    # Validate confirmation phrase
    if not request.confirmation_phrase or request.confirmation_phrase.strip().upper() != "ACTIVATE GRAPH REVISION":
        raise HTTPException(
            status_code=400,
            detail="confirmation_phrase is required and must be exactly 'ACTIVATE GRAPH REVISION'",
        )

    # Check eligibility
    from app.learning_engine.graph_revision.eligibility import is_graph_revision_eligible_for_activation

    eligible, reasons = await is_graph_revision_eligible_for_activation(db)

    if not eligible and not request.force:
        raise HTTPException(
            status_code=400,
            detail=f"Graph revision not eligible for activation: {reasons}",
        )

    # Update runtime config
    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=500, detail="Runtime config not found")

    config_json = config.config_json or {}
    overrides = config_json.get("overrides", {})
    overrides[MODULE_GRAPH_REVISION] = "v1"
    config_json["overrides"] = overrides
    config.config_json = config_json

    # Create activation event
    event = GraphRevisionActivationEvent(
        previous_state={"mode": "shadow"},
        new_state={"mode": "v1", "reason": request.reason},
        reason=request.reason,
        confirmation_phrase=request.confirmation_phrase,
        created_by_user_id=current_user.id,
    )

    db.add(event)
    await db.commit()

    return {"message": "Graph revision activated", "eligible": eligible, "reasons": reasons}


# --- POST /v1/admin/graph-revision/deactivate ---


@router.post("/admin/graph-revision/deactivate")
async def deactivate_graph_revision_endpoint(
    request: GraphRevisionDeactivateRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Deactivate graph revision (kill-switch, admin only)."""
    require_admin(current_user)

    # Validate confirmation phrase
    if not request.confirmation_phrase or request.confirmation_phrase.strip().upper() != "DEACTIVATE GRAPH REVISION":
        raise HTTPException(
            status_code=400,
            detail="confirmation_phrase is required and must be exactly 'DEACTIVATE GRAPH REVISION'",
        )

    # Update runtime config
    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=500, detail="Runtime config not found")

    config_json = config.config_json or {}
    overrides = config_json.get("overrides", {})
    overrides[MODULE_GRAPH_REVISION] = "v0"
    config_json["overrides"] = overrides
    config.config_json = config_json

    # Create deactivation event
    event = GraphRevisionActivationEvent(
        previous_state={"mode": "v1"},
        new_state={"mode": "v0", "reason": request.reason},
        reason=request.reason,
        confirmation_phrase=request.confirmation_phrase,
        created_by_user_id=current_user.id,
    )

    db.add(event)
    await db.commit()

    return {"message": "Graph revision deactivated"}
