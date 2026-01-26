"""Admin endpoints for algorithm runtime configuration and kill switch."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.audit import write_audit_critical
from app.core.dependencies import get_current_user, get_db
from app.core.errors import get_request_id
from app.security.admin_freeze import check_admin_freeze
from app.security.rate_limit import create_user_rate_limit_dep
from app.learning_engine.runtime import (
    AlgoRuntimeConfigData,
    AlgoRuntimeProfile,
    get_algo_runtime_config,
)
from app.models.algo_runtime import AlgoRuntimeConfig, AlgoSwitchEvent
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require admin role."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


# --- Schemas ---


class AlgoRuntimeStatusResponse(BaseModel):
    """Current runtime configuration status."""

    config: dict[str, Any]
    active_since: str
    last_switch_events: list[dict[str, Any]]
    bridge_job_health: dict[str, Any]


class AlgoSwitchRequest(BaseModel):
    """Request to switch algorithm profile."""

    profile: str  # "V1_PRIMARY" | "V0_FALLBACK"
    overrides: dict[str, str] | None = None  # Optional per-module overrides
    reason: str
    confirmation_phrase: str | None = None  # Typed confirmation phrase
    co_approver_code: str | None = None  # Optional co-approver code


class AlgoFreezeRequest(BaseModel):
    """Request to freeze/unfreeze updates."""

    reason: str
    confirmation_phrase: str | None = None  # Typed confirmation phrase
    co_approver_code: str | None = None  # Optional co-approver code


# --- GET /v1/admin/algorithms/runtime ---


@router.get("/admin/algorithms/runtime", response_model=AlgoRuntimeStatusResponse)
async def get_algo_runtime_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current algorithm runtime configuration and status."""
    require_admin(current_user)

    config = await get_algo_runtime_config(db)

    # Get last 10 switch events
    stmt = (
        select(AlgoSwitchEvent)
        .order_by(AlgoSwitchEvent.created_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    # Get bridge job health (counts by status)
    from app.models.algo_runtime import AlgoStateBridge
    from sqlalchemy import func

    stmt_bridge = select(
        AlgoStateBridge.status,
        func.count(AlgoStateBridge.id).label("count"),
    ).group_by(AlgoStateBridge.status)
    result_bridge = await db.execute(stmt_bridge)
    bridge_counts = {row.status: row.count for row in result_bridge.all()}

    # Get IRT effective state
    from app.learning_engine.runtime import get_effective_irt_state, get_rank_mode, is_rank_enabled_for_admin

    irt_state = await get_effective_irt_state(db)
    rank_mode = await get_rank_mode(db, config)
    rank_enabled_admin = await is_rank_enabled_for_admin(db, config)

    return AlgoRuntimeStatusResponse(
        config={
            "active_profile": config.active_profile.value,
            "overrides": config.overrides,
            "safe_mode": config.safe_mode,
            "irt": irt_state,  # Include IRT state
            "rank": {
                "mode": rank_mode,
                "enabled_for_admin": rank_enabled_admin,
                "frozen": config.safe_mode.get("freeze_updates", False),
            },
        },
        active_since=config.active_since.isoformat() if config.active_since else "",
        last_switch_events=[
            {
                "id": str(e.id),
                "previous_config": e.previous_config,
                "new_config": e.new_config,
                "reason": e.reason,
                "created_at": e.created_at.isoformat(),
                "created_by": str(e.created_by_user_id),
            }
            for e in events
        ],
        bridge_job_health={
            "counts_by_status": bridge_counts,
            "total": sum(bridge_counts.values()),
        },
    )


# --- POST /v1/admin/algorithms/runtime/switch ---


@router.post(
    "/admin/algorithms/runtime/switch",
    dependencies=[Depends(create_user_rate_limit_dep("admin.runtime_switch", fail_open=False))],
)
async def switch_algo_profile(
    request_data: AlgoSwitchRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Switch algorithm runtime profile (V1_PRIMARY ⇄ V0_FALLBACK)."""
    require_admin(current_user)
    
    # Validate reason (required for critical actions)
    if not request_data.reason or not request_data.reason.strip():
        raise HTTPException(
            status_code=400,
            detail="Reason is required for critical actions",
        )
    reason = request_data.reason.strip()
    
    # Validate profile
    try:
        new_profile = AlgoRuntimeProfile(request_data.profile)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile. Must be V1_PRIMARY or V0_FALLBACK, got: {request_data.profile}",
        )

    # Get current config to check for profile change (using sync session)
    config = db.query(AlgoRuntimeConfig).first()
    if not config:
        # Create default if missing
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={
                "profile": "V1_PRIMARY",
                "overrides": {},
                "safe_mode": {"freeze_updates": False, "prefer_cache": True},
                "search_engine_mode": "postgres",
            },
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    
    current_profile = AlgoRuntimeProfile(config.active_profile.value)
    has_profile_change = current_profile != new_profile

    # Check admin freeze and approval requirements
    check_admin_freeze(db)
    
    # Check if two-person approval required (production only)
    if has_profile_change:
        from app.api.v1.endpoints.admin_approvals import (
            check_approval_required_or_raise,
            requires_two_person_approval,
        )
        
        # Map profile to action type
        if new_profile == AlgoRuntimeProfile.V1_PRIMARY:
            approval_action_type = "PROFILE_SWITCH_PRIMARY"
        elif new_profile == AlgoRuntimeProfile.V0_FALLBACK:
            approval_action_type = "PROFILE_SWITCH_FALLBACK"
        else:
            approval_action_type = None
        
        if approval_action_type and requires_two_person_approval(approval_action_type):
            # Check for pending approval or raise 409
            check_approval_required_or_raise(db, approval_action_type, current_user, request)

    # Validate confirmation phrase
    from app.api.v1.endpoints.admin_algorithms_validation import validate_confirmation_phrase
    has_overrides = request_data.overrides and len(request_data.overrides) > 0

    if has_profile_change:
        action_type = "PROFILE_SWITCH"
    elif has_overrides:
        action_type = "OVERRIDES_APPLY"
    else:
        action_type = "OVERRIDES_APPLY"  # Default for override-only changes

    is_valid, error_msg = validate_confirmation_phrase(
        action_type=action_type,
        phrase=request_data.confirmation_phrase,
        target_profile=request_data.profile if has_profile_change else None,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg or "Invalid confirmation phrase")

    # Validate overrides
    if request_data.overrides:
        valid_modules = ["mastery", "revision", "difficulty", "adaptive", "mistakes"]
        for module, version in request_data.overrides.items():
            if module not in valid_modules:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid module in overrides: {module}. Must be one of {valid_modules}",
                )
            if version not in ("v0", "v1"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid version for {module}: {version}. Must be v0 or v1",
                )

    # Prepare previous config for audit
    previous_config = {
        "active_profile": config.active_profile.value,
        "config_json": config.config_json,
        "active_since": config.active_since.isoformat() if config.active_since else None,
    }

    # Update config
    config.active_profile = new_profile
    config.active_since = datetime.now(UTC)
    config.reason = reason
    config.changed_by_user_id = current_user.id

    # Update config_json
    config_json = config.config_json or {}
    config_json["profile"] = new_profile.value
    if request_data.overrides:
        config_json["overrides"] = request_data.overrides
    else:
        config_json["overrides"] = {}
    config.config_json = config_json

    # Prepare new config for audit
    new_config = {
        "active_profile": new_profile.value,
        "config_json": config_json,
        "active_since": config.active_since.isoformat(),
    }

    # Create audit event (include confirmation phrase in details)
    event_details = {
        "confirmation_phrase_provided": bool(request_data.confirmation_phrase),
        "co_approver_code_provided": bool(request_data.co_approver_code),
    }
    switch_event = AlgoSwitchEvent(
        previous_config=previous_config,
        new_config={**new_config, "details": event_details},
        reason=reason,
        created_by_user_id=current_user.id,
    )
    db.add(switch_event)

    db.commit()
    db.refresh(config)

    # Write audit log
    from uuid import uuid4
    
    request_id = get_request_id(request)
    write_audit_critical(
        db=db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="ALGO_MODE_SWITCH",
        entity_type="ALGO_RUNTIME",
        entity_id=uuid4(),
        reason=reason,
        request=request,
        before=previous_config,
        after=new_config,
        meta={"request_id": request_id, "action_type": action_type},
    )

    logger.info(
        f"Algorithm profile switched from {previous_config['active_profile']} to {new_profile.value} "
        f"by {current_user.email}. Reason: {reason}"
    )

    return {
        "message": "Algorithm profile switched successfully",
        "previous_profile": previous_config["active_profile"],
        "new_profile": new_profile.value,
        "overrides": request_data.overrides or {},
    }


# --- POST /v1/admin/algorithms/runtime/freeze_updates ---


@router.post("/admin/algorithms/runtime/freeze_updates")
async def freeze_updates(
    request: AlgoFreezeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Enable safe mode freeze_updates (emergency read-only mode)."""
    require_admin(current_user)

    # Validate confirmation phrase
    from app.api.v1.endpoints.admin_algorithms_validation import validate_confirmation_phrase

    is_valid, error_msg = validate_confirmation_phrase(
        action_type="FREEZE",
        phrase=request.confirmation_phrase,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg or "Invalid confirmation phrase")

    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=500, detail="Runtime config not found")

    config_json = config.config_json or {}
    safe_mode = config_json.get("safe_mode", {})
    safe_mode["freeze_updates"] = True
    config_json["safe_mode"] = safe_mode
    config.config_json = config_json
    config.changed_by_user_id = current_user.id

    await db.commit()

    logger.warning(f"Safe mode freeze_updates enabled by {current_user.email}. Reason: {request.reason}")

    return {"message": "Updates frozen. System is now in read-only mode.", "frozen": True}


# --- POST /v1/admin/algorithms/runtime/unfreeze_updates ---


@router.post("/admin/algorithms/runtime/unfreeze_updates")
async def unfreeze_updates(
    request: AlgoFreezeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Disable safe mode freeze_updates."""
    require_admin(current_user)

    # Validate confirmation phrase
    from app.api.v1.endpoints.admin_algorithms_validation import validate_confirmation_phrase

    is_valid, error_msg = validate_confirmation_phrase(
        action_type="UNFREEZE",
        phrase=request.confirmation_phrase,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg or "Invalid confirmation phrase")

    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=500, detail="Runtime config not found")

    config_json = config.config_json or {}
    safe_mode = config_json.get("safe_mode", {})
    safe_mode["freeze_updates"] = False
    config_json["safe_mode"] = safe_mode
    config.config_json = config_json
    config.changed_by_user_id = current_user.id

    await db.commit()

    logger.info(f"Safe mode freeze_updates disabled by {current_user.email}. Reason: {request.reason}")

    return {"message": "Updates unfrozen. System is now in normal mode.", "frozen": False}


# --- GET /v1/admin/algorithms/bridge/status ---


@router.get("/admin/algorithms/bridge/status")
async def get_bridge_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    user_id: UUID | None = None,
):
    """Get bridge status for a user or all users."""
    require_admin(current_user)

    from app.models.algo_runtime import AlgoStateBridge

    if user_id:
        stmt = (
            select(AlgoStateBridge)
            .where(AlgoStateBridge.user_id == user_id)
            .order_by(AlgoStateBridge.started_at.desc())
            .limit(10)
        )
        result = await db.execute(stmt)
        bridges = result.scalars().all()

        return {
            "user_id": str(user_id),
            "bridges": [
                {
                    "id": str(b.id),
                    "from_profile": b.from_profile.value,
                    "to_profile": b.to_profile.value,
                    "status": b.status,
                    "started_at": b.started_at.isoformat() if b.started_at else None,
                    "finished_at": b.finished_at.isoformat() if b.finished_at else None,
                    "details": b.details_json,
                }
                for b in bridges
            ],
        }
    else:
        # Aggregate stats
        from sqlalchemy import func

        stmt = select(
            AlgoStateBridge.status,
            func.count(AlgoStateBridge.id).label("count"),
        ).group_by(AlgoStateBridge.status)
        result = await db.execute(stmt)
        counts = {row.status: row.count for row in result.all()}

        return {
            "summary": {
                "counts_by_status": counts,
                "total": sum(counts.values()),
            },
        }
