"""IRT (Item Response Theory) admin API — shadow/offline only."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.learning_engine.irt.activation_policy import evaluate_irt_activation
from app.learning_engine.irt.dataset import IRTDatasetSpec
from app.learning_engine.irt.registry import (
    create_irt_run,
    get_irt_run,
    list_irt_runs,
)
from app.learning_engine.irt.runner import run_irt_calibration
from app.models.irt import IrtCalibrationRun, IrtItemParams, IrtUserAbility
from app.models.irt_activation import (
    IrtActivationDecision,
    IrtActivationEvent,
    IrtActivationEventType,
)
from app.models.platform_settings import PlatformSettings
from app.models.user import User
from app.security.exam_mode_gate import require_not_exam_mode

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


def require_irt_shadow() -> None:
    if not getattr(settings, "FEATURE_IRT_SHADOW", True):
        raise HTTPException(
            status_code=403,
            detail="IRT (shadow) is disabled. Set FEATURE_IRT_SHADOW=true to use.",
        )


# --- Schemas ---


class IrtRunCreate(BaseModel):
    model_type: str  # IRT_2PL | IRT_3PL
    dataset_spec: dict[str, Any]
    seed: int = 42
    notes: str | None = None


class IrtRunResponse(BaseModel):
    id: str
    model_type: str
    dataset_spec: dict[str, Any]
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    seed: int
    notes: str | None
    error: str | None
    metrics: dict[str, Any] | None
    artifact_paths: dict[str, str] | None
    eval_run_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# --- POST /v1/admin/irt/runs ---


@router.post(
    "/admin/irt/runs",
    response_model=IrtRunResponse,
    dependencies=[Depends(require_not_exam_mode("irt_calibration"))],
)
async def create_irt_run_endpoint(
    request: IrtRunCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create IRT calibration run and execute (admin only)."""
    require_admin(current_user)
    
    require_irt_shadow()

    # Check runtime config for IRT shadow enablement
    from app.learning_engine.runtime import is_irt_shadow_enabled

    if not await is_irt_shadow_enabled(db):
        raise HTTPException(
            status_code=403,
            detail="IRT shadow mode is disabled. Enable via runtime config or platform_settings.",
        )

    if request.model_type not in ("IRT_2PL", "IRT_3PL"):
        raise HTTPException(status_code=400, detail="model_type must be IRT_2PL or IRT_3PL")

    try:
        IRTDatasetSpec(**request.dataset_spec)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid dataset_spec: {e}")

    run = await create_irt_run(
        db,
        model_type=request.model_type,
        dataset_spec=request.dataset_spec,
        seed=request.seed,
        notes=request.notes,
    )

    try:
        await run_irt_calibration(db, run.id)
    except Exception as e:
        logger.exception("IRT calibration failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Calibration failed: {str(e)}")

    r = await get_irt_run(db, run.id)
    if not r:
        raise HTTPException(status_code=404, detail="Run not found after creation")
    return IrtRunResponse(
        id=str(r.id),
        model_type=r.model_type,
        dataset_spec=r.dataset_spec or {},
        status=r.status,
        started_at=r.started_at,
        finished_at=r.finished_at,
        seed=r.seed,
        notes=r.notes,
        error=r.error,
        metrics=r.metrics,
        artifact_paths=r.artifact_paths,
        eval_run_id=str(r.eval_run_id) if r.eval_run_id else None,
        created_at=r.created_at,
    )


# --- GET /v1/admin/irt/runs ---


@router.get("/admin/irt/runs", response_model=list[IrtRunResponse])
async def list_irt_runs_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    model_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
):
    """List IRT calibration runs (admin only)."""
    require_admin(current_user)
    require_irt_shadow()

    runs = await list_irt_runs(db, model_type=model_type, status=status, limit=limit)
    return [
        IrtRunResponse(
            id=str(r.id),
            model_type=r.model_type,
            dataset_spec=r.dataset_spec or {},
            status=r.status,
            started_at=r.started_at,
            finished_at=r.finished_at,
            seed=r.seed,
            notes=r.notes,
            error=r.error,
            metrics=r.metrics,
            artifact_paths=r.artifact_paths,
            eval_run_id=str(r.eval_run_id) if r.eval_run_id else None,
            created_at=r.created_at,
        )
        for r in runs
    ]


# --- GET /v1/admin/irt/runs/{id} ---


@router.get("/admin/irt/runs/{run_id}", response_model=dict[str, Any])
async def get_irt_run_endpoint(
    run_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get IRT run details + metrics (admin only)."""
    require_admin(current_user)
    require_irt_shadow()

    from uuid import UUID

    rid = UUID(run_id)
    run = await get_irt_run(db, rid)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "run": IrtRunResponse(
            id=str(run.id),
            model_type=run.model_type,
            dataset_spec=run.dataset_spec or {},
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            seed=run.seed,
            notes=run.notes,
            error=run.error,
            metrics=run.metrics,
            artifact_paths=run.artifact_paths,
            eval_run_id=str(run.eval_run_id) if run.eval_run_id else None,
            created_at=run.created_at,
        ).model_dump(),
    }


# --- GET /v1/admin/irt/runs/{id}/items ---


@router.get("/admin/irt/runs/{run_id}/items", response_model=list[dict[str, Any]])
async def list_irt_run_items_endpoint(
    run_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    flag: str | None = None,
):
    """List item params for a run, optionally filtered by flag (admin only)."""
    require_admin(current_user)
    require_irt_shadow()

    from uuid import UUID

    rid = UUID(run_id)
    run = await get_irt_run(db, rid)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    stmt = select(IrtItemParams).where(IrtItemParams.run_id == rid)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    out = []
    for r in rows:
        fl = r.flags or {}
        if flag and flag not in fl:
            continue
        if flag and not fl.get(flag):
            continue
        out.append({
            "question_id": str(r.question_id),
            "a": r.a,
            "b": r.b,
            "c": r.c,
            "a_se": r.a_se,
            "b_se": r.b_se,
            "c_se": r.c_se,
            "flags": fl,
        })
    return out


# --- GET /v1/admin/irt/runs/{id}/items/{question_id} ---


@router.get("/admin/irt/runs/{run_id}/items/{question_id}", response_model=dict[str, Any])
async def get_irt_run_item_endpoint(
    run_id: str,
    question_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get item params for a specific question (admin only)."""
    require_admin(current_user)
    require_irt_shadow()

    from uuid import UUID

    rid = UUID(run_id)
    qid = UUID(question_id)
    run = await get_irt_run(db, rid)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    stmt = select(IrtItemParams).where(
        IrtItemParams.run_id == rid,
        IrtItemParams.question_id == qid,
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    return {
        "question_id": str(row.question_id),
        "a": row.a,
        "b": row.b,
        "c": row.c,
        "a_se": row.a_se,
        "b_se": row.b_se,
        "c_se": row.c_se,
        "flags": row.flags or {},
    }


# --- GET /v1/admin/irt/runs/{id}/users/{user_id} ---


@router.get("/admin/irt/runs/{run_id}/users/{user_id}", response_model=dict[str, Any])
async def get_irt_run_user_endpoint(
    run_id: str,
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get user ability (theta + se) for a run (admin only)."""
    require_admin(current_user)
    require_irt_shadow()

    from uuid import UUID

    rid = UUID(run_id)
    uid = UUID(user_id)
    run = await get_irt_run(db, rid)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    stmt = select(IrtUserAbility).where(
        IrtUserAbility.run_id == rid,
        IrtUserAbility.user_id == uid,
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": str(row.user_id),
        "theta": row.theta,
        "theta_se": row.theta_se,
    }


# --- IRT Activation Endpoints ---


class IrtActivationEvaluateRequest(BaseModel):
    run_id: str
    policy_version: str = "v1"


class IrtActivationEvaluateResponse(BaseModel):
    decision: dict[str, Any]
    eligible: bool
    gates: list[dict[str, Any]]


@router.post("/admin/irt/activation/evaluate", response_model=IrtActivationEvaluateResponse)
async def evaluate_irt_activation_endpoint(
    request: IrtActivationEvaluateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Evaluate IRT activation gates for a calibration run (admin only)."""
    require_admin(current_user)
    require_irt_shadow()

    run_id = UUID(request.run_id)

    # Get run
    run = await db.get(IrtCalibrationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="IRT calibration run not found")

    # Evaluate activation
    decision = await evaluate_irt_activation(db, run_id, run.model_type, request.policy_version)

    # Save decision
    decision_obj = IrtActivationDecision(
        run_id=run_id,
        policy_version=request.policy_version,
        decision_json={
            "eligible": decision.eligible,
            "policy_version": decision.policy_version,
            "evaluated_at": decision.evaluated_at.isoformat(),
            "gates": [
                {
                    "name": g.name,
                    "passed": g.passed,
                    "value": g.value,
                    "threshold": g.threshold,
                    "notes": g.notes,
                }
                for g in decision.gates
            ],
            "recommended_scope": decision.recommended_scope,
            "recommended_model": decision.recommended_model,
            "requires_human_ack": decision.requires_human_ack,
        },
        eligible=decision.eligible,
        created_by_user_id=current_user.id,
    )
    db.add(decision_obj)

    # Create audit event
    event = IrtActivationEvent(
        event_type=IrtActivationEventType.EVALUATED,
        previous_state=None,
        new_state={"eligible": decision.eligible, "gates_passed": sum(1 for g in decision.gates if g.passed)},
        run_id=run_id,
        policy_version=request.policy_version,
        reason=f"Activation evaluation by {current_user.email}",
        created_by_user_id=current_user.id,
    )
    db.add(event)

    await db.commit()

    return IrtActivationEvaluateResponse(
        decision={
            "eligible": decision.eligible,
            "policy_version": decision.policy_version,
            "evaluated_at": decision.evaluated_at.isoformat(),
            "recommended_scope": decision.recommended_scope,
            "recommended_model": decision.recommended_model,
        },
        eligible=decision.eligible,
        gates=[
            {
                "name": g.name,
                "passed": g.passed,
                "value": g.value,
                "threshold": g.threshold,
                "notes": g.notes,
            }
            for g in decision.gates
        ],
    )


class IrtActivationActivateRequest(BaseModel):
    run_id: str
    scope: str  # "selection_only" | "scoring_only" | "selection_and_scoring"
    model_type: str  # "IRT_2PL" | "IRT_3PL"
    reason: str
    confirmation_phrase: str | None = None  # Typed confirmation phrase
    co_approver_code: str | None = None  # Optional co-approver code


@router.post("/admin/irt/activation/activate")
async def activate_irt_endpoint(
    request: IrtActivationActivateRequest,
    http_request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Activate IRT for student-facing decisions (admin only)."""
    require_admin(current_user)
    require_irt_shadow()

    # Check two-person approval requirement (production only)
    from app.api.v1.endpoints.admin_approvals import (
        check_approval_required_or_raise,
        requires_two_person_approval,
    )
    from app.db.session import SessionLocal
    
    # Use sync DB for approval check
    sync_db = SessionLocal()
    try:
        if requires_two_person_approval("IRT_ACTIVATE"):
            check_approval_required_or_raise(sync_db, "IRT_ACTIVATE", current_user, http_request)
    finally:
        sync_db.close()

    # Validate confirmation phrase
    if not request.confirmation_phrase or request.confirmation_phrase.strip().upper() != "ACTIVATE IRT":
        raise HTTPException(
            status_code=400,
            detail="confirmation_phrase is required and must be exactly 'ACTIVATE IRT'",
        )

    run_id = UUID(request.run_id)

    # Validate scope
    if request.scope not in ("selection_only", "scoring_only", "selection_and_scoring"):
        raise HTTPException(status_code=400, detail="Invalid scope. Must be selection_only, scoring_only, or selection_and_scoring")

    # Validate model_type
    if request.model_type not in ("IRT_2PL", "IRT_3PL"):
        raise HTTPException(status_code=400, detail="Invalid model_type. Must be IRT_2PL or IRT_3PL")

    # Get latest decision
    stmt = (
        select(IrtActivationDecision)
        .where(IrtActivationDecision.run_id == run_id)
        .order_by(IrtActivationDecision.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    latest_decision = result.scalar_one_or_none()

    if not latest_decision:
        raise HTTPException(status_code=400, detail="No activation decision found. Run evaluation first.")

    if not latest_decision.eligible:
        raise HTTPException(status_code=400, detail="Cannot activate: run is not eligible. All gates must pass.")

    # Get current state
    current_active = await _get_irt_flag(db, "active", False)
    current_scope = await _get_irt_flag(db, "scope", "none")
    current_model = await _get_irt_flag(db, "model", "IRT_2PL")

    previous_state = {
        "active": current_active,
        "scope": current_scope,
        "model": current_model,
    }

    # Update platform_settings
    await _update_irt_flags(db, current_user.id, active=True, scope=request.scope, model=request.model_type)

    new_state = {
        "active": True,
        "scope": request.scope,
        "model": request.model_type,
    }

    # Create audit event (include confirmation phrase status)
    event_details = {
        "confirmation_phrase_provided": bool(request.confirmation_phrase),
        "co_approver_code_provided": bool(request.co_approver_code),
    }
    event = IrtActivationEvent(
        event_type=IrtActivationEventType.ACTIVATED,
        previous_state=previous_state,
        new_state={**new_state, "details": event_details},
        run_id=run_id,
        policy_version=latest_decision.policy_version,
        reason=request.reason or f"Activated by {current_user.email}",
        created_by_user_id=current_user.id,
    )
    db.add(event)
    await db.commit()

    return {"message": "IRT activated successfully", "state": new_state}


class IrtActivationDeactivateRequest(BaseModel):
    reason: str
    confirmation_phrase: str | None = None  # Typed confirmation phrase
    co_approver_code: str | None = None  # Optional co-approver code


@router.post("/admin/irt/activation/deactivate")
async def deactivate_irt_endpoint(
    request: IrtActivationDeactivateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Deactivate IRT (kill-switch, admin only)."""
    require_admin(current_user)

    # Validate confirmation phrase
    if not request.confirmation_phrase or request.confirmation_phrase.upper() != "DEACTIVATE IRT":
        raise HTTPException(
            status_code=400,
            detail="confirmation_phrase is required and must be exactly 'DEACTIVATE IRT'",
        )

    # Get current state
    current_active = await _get_irt_flag(db, "active", False)
    current_scope = await _get_irt_flag(db, "scope", "none")
    current_model = await _get_irt_flag(db, "model", "IRT_2PL")

    previous_state = {
        "active": current_active,
        "scope": current_scope,
        "model": current_model,
    }

    # Update platform_settings (force deactivation)
    await _update_irt_flags(db, current_user.id, active=False, scope="none", model="IRT_2PL")

    new_state = {
        "active": False,
        "scope": "none",
        "model": "IRT_2PL",
    }

    # Create audit event
    event = IrtActivationEvent(
        event_type=IrtActivationEventType.DEACTIVATED,
        previous_state=previous_state,
        new_state=new_state,
        run_id=None,  # Deactivation not tied to a specific run
        policy_version=None,
        reason=request.reason or f"Deactivated by {current_user.email}",
        created_by_user_id=current_user.id,
    )
    db.add(event)
    await db.commit()

    return {"message": "IRT deactivated successfully", "state": new_state}


@router.get("/admin/irt/activation/status")
async def get_irt_activation_status_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current IRT activation status (admin only)."""
    require_admin(current_user)

    # Get current flags
    active = await _get_irt_flag(db, "active", False)
    scope = await _get_irt_flag(db, "scope", "none")
    model = await _get_irt_flag(db, "model", "IRT_2PL")
    shadow = await _get_irt_flag(db, "shadow", True)

    # Get latest decision for latest run
    stmt = (
        select(IrtActivationDecision)
        .order_by(IrtActivationDecision.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    latest_decision = result.scalar_one_or_none()

    # Get last 10 activation events
    stmt_events = (
        select(IrtActivationEvent)
        .order_by(IrtActivationEvent.created_at.desc())
        .limit(10)
    )
    result_events = await db.execute(stmt_events)
    events = result_events.scalars().all()

    return {
        "flags": {
            "active": active,
            "scope": scope,
            "model": model,
            "shadow": shadow,
        },
        "latest_decision": {
            "eligible": latest_decision.eligible if latest_decision else None,
            "run_id": str(latest_decision.run_id) if latest_decision else None,
            "created_at": latest_decision.created_at.isoformat() if latest_decision else None,
        },
        "recent_events": [
            {
                "event_type": e.event_type.value,
                "created_at": e.created_at.isoformat(),
                "created_by": str(e.created_by_user_id),
                "reason": e.reason,
            }
            for e in events
        ],
    }


# Helper functions for platform_settings


async def _get_irt_flag(db: AsyncSession, flag_name: str, default: Any) -> Any:
    """Get IRT flag from platform_settings."""
    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if settings and settings.data and "irt" in settings.data:
        return settings.data["irt"].get(flag_name, default)
    return default


async def _update_irt_flags(
    db: AsyncSession,
    user_id: UUID,
    active: bool | None = None,
    scope: str | None = None,
    model: str | None = None,
) -> None:
    """Update IRT flags in platform_settings."""
    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if not settings:
        # Create default settings
        settings = PlatformSettings(id=1, data={})
        db.add(settings)

    if not settings.data:
        settings.data = {}

    if "irt" not in settings.data:
        settings.data["irt"] = {}

    if active is not None:
        settings.data["irt"]["active"] = active
    if scope is not None:
        settings.data["irt"]["scope"] = scope
    if model is not None:
        settings.data["irt"]["model"] = model

    settings.updated_at = datetime.now(UTC)
    settings.updated_by_user_id = user_id

    await db.commit()
