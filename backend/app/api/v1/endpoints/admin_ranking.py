"""Admin ranking API: runtime, switch (police), compute, runs (Task 145)."""

from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.api.v1.endpoints.admin_algorithms_validation import validate_confirmation_phrase
from app.core.dependencies import get_current_user, get_db
from app.models.ranking_mock import RankingRun, RankingRunStatus
from app.models.user import User
from app.ranking.runtime import (
    RANKING_MODE_GO_ACTIVE,
    RANKING_MODE_DISABLED,
    RANKING_MODE_GO_SHADOW,
    RANKING_MODE_PYTHON,
    evaluate_ranking_readiness_for_go,
    get_effective_ranking_engine,
    get_ranking_mode,
    get_recent_parity,
    is_ranking_frozen,
)
from app.ranking.service import compute_ranking
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_admin(user: User) -> None:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


# --- Schemas ---


class RankingRuntimeResponse(BaseModel):
    """GET /admin/ranking/runtime."""

    requested_mode: str
    effective_mode: str
    freeze: bool
    warnings: list[str]
    readiness: dict[str, Any] | None = None
    recent_parity: dict[str, Any] | None = None


class RankingSwitchRequest(BaseModel):
    """POST /admin/ranking/runtime/switch."""

    mode: str = Field(..., description="disabled | python | go_shadow | go_active")
    reason: str = Field(..., min_length=1)
    confirmation_phrase: str = Field(...)


class RankingComputeRequest(BaseModel):
    """POST /admin/ranking/compute."""

    mock_instance_id: UUID = Field(...)
    cohort_id: str = Field(..., min_length=1)
    engine_requested: str | None = Field(default=None)
    reason: str = Field(..., min_length=1)
    confirmation_phrase: str = Field(...)


class RankingRunResponse(BaseModel):
    """Single ranking run."""

    id: str
    mock_instance_id: str
    cohort_id: str
    status: str
    engine_requested: str | None
    engine_effective: str | None
    started_at: str | None
    finished_at: str | None
    n_users: int | None
    last_error: str | None
    parity_report: dict[str, Any] | None
    created_at: str


# --- GET /v1/admin/ranking/runtime ---


@router.get("/admin/ranking/runtime", response_model=RankingRuntimeResponse)
def get_ranking_runtime(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Get ranking runtime config (mode, effective engine, freeze, readiness)."""
    _require_admin(current_user)

    mode = get_ranking_mode(db)
    effective, warnings = get_effective_ranking_engine(db)
    if mode == RANKING_MODE_DISABLED:
        effective = RANKING_MODE_DISABLED
    frozen = is_ranking_frozen(db)

    readiness = None
    if mode in (RANKING_MODE_GO_SHADOW, RANKING_MODE_GO_ACTIVE):
        _, result = evaluate_ranking_readiness_for_go(db)
        readiness = {
            "ready": result.ready,
            "checks": result.checks,
            "blocking_reasons": result.blocking_reasons,
        }

    recent_parity = get_recent_parity(db)

    return RankingRuntimeResponse(
        requested_mode=mode,
        effective_mode=effective,
        freeze=frozen,
        warnings=warnings,
        readiness=readiness,
        recent_parity=recent_parity,
    )


# --- POST /v1/admin/ranking/runtime/switch (police) ---


@router.post("/admin/ranking/runtime/switch", response_model=RankingRuntimeResponse)
def switch_ranking_runtime(
    request: RankingSwitchRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Switch ranking mode. Police: phrase + reason required."""
    _require_admin(current_user)

    if request.mode not in (RANKING_MODE_DISABLED, RANKING_MODE_PYTHON, RANKING_MODE_GO_SHADOW, RANKING_MODE_GO_ACTIVE):
        raise HTTPException(status_code=400, detail="Invalid mode: disabled | python | go_shadow | go_active")

    action_map = {
        RANKING_MODE_DISABLED: "RANKING_DISABLED",
        RANKING_MODE_PYTHON: "RANKING_PYTHON",
        RANKING_MODE_GO_SHADOW: "RANKING_GO_SHADOW",
        RANKING_MODE_GO_ACTIVE: "RANKING_GO_ACTIVE",
    }
    action = action_map[request.mode]
    ok, err = validate_confirmation_phrase(action, request.confirmation_phrase)
    if not ok:
        raise HTTPException(status_code=400, detail=err or "Invalid confirmation phrase")

    from app.models.algo_runtime import AlgoRuntimeConfig

    row = db.query(AlgoRuntimeConfig).order_by(AlgoRuntimeConfig.updated_at.desc()).first()
    if not row:
        raise HTTPException(status_code=500, detail="No algo_runtime_config found")

    cfg = dict(row.config_json or {})
    cfg["ranking_mode"] = request.mode
    row.config_json = cfg
    row.reason = request.reason
    row.changed_by_user_id = current_user.id
    db.commit()

    return get_ranking_runtime(current_user=current_user, db=db)


# --- POST /v1/admin/ranking/compute ---


@router.post("/admin/ranking/compute")
def compute_ranking_endpoint(
    request: RankingComputeRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Compute ranking for (mock_instance_id, cohort_id). Returns run id. Police: phrase + reason."""
    _require_admin(current_user)

    ok, err = validate_confirmation_phrase("RANKING_COMPUTE", request.confirmation_phrase)
    if not ok:
        raise HTTPException(status_code=400, detail=err or "Invalid confirmation phrase")

    if get_ranking_mode(db) == "disabled":
        raise HTTPException(status_code=403, detail="Ranking is disabled")

    if is_ranking_frozen(db):
        raise HTTPException(status_code=403, detail="Ranking updates frozen")

    try:
        run_id = compute_ranking(
            db,
            request.mock_instance_id,
            request.cohort_id,
            request.engine_requested,
            current_user.id,
        )
        return {"ranking_run_id": str(run_id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- GET /v1/admin/ranking/runs ---


@router.get("/admin/ranking/runs")
def list_ranking_runs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)] = None,
    limit: int = 50,
):
    """List recent ranking runs."""
    _require_admin(current_user)

    stmt = (
        select(RankingRun)
        .order_by(desc(RankingRun.created_at))
        .limit(min(limit, 100))
    )
    runs = list(db.execute(stmt).scalars().all())

    def _str_status(s):
        return getattr(s, "value", s) if s is not None else None

    return {
        "runs": [
            {
                "id": str(r.id),
                "mock_instance_id": str(r.mock_instance_id),
                "cohort_id": r.cohort_id,
                "status": _str_status(r.status),
                "engine_requested": r.engine_requested,
                "engine_effective": r.engine_effective,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "n_users": r.n_users,
                "last_error": r.last_error,
                "parity_report": r.parity_report,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
    }


# --- GET /v1/admin/ranking/runs/{id} ---


@router.get("/admin/ranking/runs/{run_id}", response_model=RankingRunResponse)
def get_ranking_run(
    run_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Get a single ranking run by id."""
    _require_admin(current_user)

    stmt = select(RankingRun).where(RankingRun.id == run_id)
    r = db.execute(stmt).scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="Ranking run not found")

    _str_status = lambda s: getattr(s, "value", s) if s is not None else None
    return RankingRunResponse(
        id=str(r.id),
        mock_instance_id=str(r.mock_instance_id),
        cohort_id=r.cohort_id,
        status=_str_status(r.status),
        engine_requested=r.engine_requested,
        engine_effective=r.engine_effective,
        started_at=r.started_at.isoformat() if r.started_at else None,
        finished_at=r.finished_at.isoformat() if r.finished_at else None,
        n_users=r.n_users,
        last_error=r.last_error,
        parity_report=r.parity_report,
        created_at=r.created_at.isoformat() if r.created_at else None,
    )
