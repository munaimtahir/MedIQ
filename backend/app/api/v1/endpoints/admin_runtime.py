"""Admin runtime control API: status, flags, profile, overrides."""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.app_exceptions import raise_app_error
from app.core.dependencies import get_db, require_roles
from app.models.runtime_control import ModuleOverride, RuntimeProfile, SwitchAuditLog
from app.models.user import User, UserRole
from app.runtime_control import (
    append_switch_audit,
    phrase_for_flag,
    phrase_for_profile,
    refresh_runtime_cache,
    require_confirmation,
    resolve_runtime,
)
from app.security.admin_freeze import check_admin_freeze
from app.system.flags import (
    get_exam_mode_state,
    get_flag,
    get_freeze_updates_state,
    refresh_exam_mode_cache,
    refresh_freeze_updates_cache,
    set_flag,
)

router = APIRouter(prefix="/admin/runtime", tags=["Admin - Runtime Control"])


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------

class RuntimeStatusResponse(BaseModel):
    """Current runtime status: flags, profile, overrides, resolved."""

    flags: dict[str, Any]
    active_profile: dict[str, Any]
    module_overrides: list[dict[str, Any]]
    resolved: dict[str, Any]
    last_changed: dict[str, Any] | None = None


class FlagSetRequest(BaseModel):
    """Set a system flag (EXAM_MODE, FREEZE_UPDATES)."""

    key: Literal["EXAM_MODE", "FREEZE_UPDATES"] = Field(..., description="Flag key: EXAM_MODE or FREEZE_UPDATES")
    value: bool = Field(..., description="New value")
    reason: str = Field(..., min_length=1, description="Reason (required)")
    confirmation_phrase: str = Field(..., description="Exact phrase per policy")


class ProfileSetRequest(BaseModel):
    """Set active runtime profile."""

    profile_name: Literal["primary", "fallback", "shadow"] = Field(..., description="primary | fallback | shadow")
    reason: str = Field(..., min_length=1, description="Reason (required)")
    confirmation_phrase: str = Field(..., description="SET PROFILE PRIMARY | FALLBACK | SHADOW")


class OverrideSetRequest(BaseModel):
    """Set or update module override."""

    module_key: str = Field(..., description="mastery | revision | adaptive | ...")
    version_key: str | None = Field(None, description="e.g. v0, v1, v2-shadow")
    is_enabled: bool | None = Field(None, description="For infra toggles")
    reason: str = Field(..., min_length=1, description="Reason (required)")
    confirmation_phrase: str = Field(..., description="Confirmation phrase")


# -----------------------------------------------------------------------------
# GET /status
# -----------------------------------------------------------------------------

@router.get("/status", response_model=RuntimeStatusResponse)
def get_runtime_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> RuntimeStatusResponse:
    """Get current runtime status: flags, profile, overrides, resolved effective runtime."""
    exam = get_exam_mode_state(db)
    freeze = get_freeze_updates_state(db)
    flags = {
        "EXAM_MODE": exam,
        "FREEZE_UPDATES": freeze,
    }

    active = db.query(RuntimeProfile).filter(RuntimeProfile.is_active.is_(True)).first()
    active_profile = {}
    if active:
        active_profile = {
            "name": active.name,
            "config": active.config,
            "updated_at": active.updated_at.isoformat() if active.updated_at else None,
        }

    overrides = db.query(ModuleOverride).all()
    module_overrides = [
        {"module_key": r.module_key, "version_key": r.version_key, "is_enabled": r.is_enabled, "updated_at": r.updated_at.isoformat() if r.updated_at else None}
        for r in overrides
    ]

    resolved = resolve_runtime(db, use_cache=True)
    # Serialize for JSON (datetime etc.)
    resolved_out = {
        "profile": resolved.get("profile"),
        "modules": resolved.get("modules"),
        "feature_toggles": resolved.get("feature_toggles"),
        "freeze_updates": resolved.get("freeze_updates"),
        "exam_mode": resolved.get("exam_mode"),
        "source": resolved.get("source"),
    }

    last = db.query(SwitchAuditLog).order_by(SwitchAuditLog.created_at.desc()).first()
    last_changed = None
    if last:
        last_changed = {
            "action_type": last.action_type,
            "created_at": last.created_at.isoformat() if last.created_at else None,
            "actor_user_id": str(last.actor_user_id) if last.actor_user_id else None,
        }

    return RuntimeStatusResponse(
        flags=flags,
        active_profile=active_profile,
        module_overrides=module_overrides,
        resolved=resolved_out,
        last_changed=last_changed,
    )


# -----------------------------------------------------------------------------
# POST /flags
# -----------------------------------------------------------------------------

@router.post("/flags")
def set_runtime_flag(
    request_data: FlagSetRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    """Set a system flag (EXAM_MODE, FREEZE_UPDATES). Requires police-mode confirmation."""
    check_admin_freeze(db)
    expected = phrase_for_flag(request_data.key, request_data.value)
    require_confirmation(
        request,
        request_data.confirmation_phrase,
        request_data.reason,
        expected,
    )

    flag = get_flag(db, request_data.key)
    before = {"value": flag.value, "reason": flag.reason} if flag else None
    updated = set_flag(
        db=db,
        key=request_data.key,
        value=request_data.value,
        updated_by=current_user.id,
        reason=request_data.reason,
    )
    after = {"value": updated.value, "reason": updated.reason}

    append_switch_audit(
        db,
        actor_user_id=current_user.id,
        action_type="FLAG_SET",
        before=before,
        after=after,
        reason=request_data.reason,
    )
    db.commit()

    if request_data.key == "EXAM_MODE":
        refresh_exam_mode_cache(db)
    elif request_data.key == "FREEZE_UPDATES":
        refresh_freeze_updates_cache(db)
    refresh_runtime_cache(db)

    return {"key": request_data.key, "value": request_data.value, "updated_at": updated.updated_at.isoformat() if updated.updated_at else None}


# -----------------------------------------------------------------------------
# POST /profile
# -----------------------------------------------------------------------------

@router.post("/profile")
def set_runtime_profile(
    request_data: ProfileSetRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    """Set active runtime profile (primary | fallback | shadow). Requires confirmation."""
    check_admin_freeze(db)
    expected = phrase_for_profile(request_data.profile_name)
    require_confirmation(
        request,
        request_data.confirmation_phrase,
        request_data.reason,
        expected,
    )

    all_profiles = db.query(RuntimeProfile).all()
    active_before = next((p for p in all_profiles if p.is_active), None)
    before = {"name": active_before.name, "is_active": active_before.is_active} if active_before else None

    target = next((p for p in all_profiles if p.name == request_data.profile_name), None)
    if not target:
        raise_app_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PROFILE_NOT_FOUND",
            message=f"Runtime profile '{request_data.profile_name}' not found",
        )
    for p in all_profiles:
        p.is_active = p.name == request_data.profile_name
    db.commit()

    active_after = db.query(RuntimeProfile).filter(RuntimeProfile.is_active.is_(True)).first()
    after = {"name": active_after.name, "is_active": True} if active_after else None

    append_switch_audit(
        db,
        actor_user_id=current_user.id,
        action_type="PROFILE_SET",
        before=before,
        after=after,
        reason=request_data.reason,
    )
    db.commit()

    refresh_runtime_cache(db)
    return {"profile_name": request_data.profile_name, "active": True}


# -----------------------------------------------------------------------------
# POST /override
# -----------------------------------------------------------------------------

@router.post("/override")
def set_module_override(
    request_data: OverrideSetRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    """Set or update module override. Requires confirmation."""
    check_admin_freeze(db)
    to_val = request_data.version_key if request_data.version_key is not None else ("enabled" if request_data.is_enabled else "disabled")
    expected = f"OVERRIDE MODULE {request_data.module_key} TO {to_val}"
    require_confirmation(
        request,
        request_data.confirmation_phrase,
        request_data.reason,
        expected,
    )

    row = db.query(ModuleOverride).filter(ModuleOverride.module_key == request_data.module_key).first()
    before = None
    if row:
        before = {"module_key": row.module_key, "version_key": row.version_key, "is_enabled": row.is_enabled}
    else:
        ver = request_data.version_key if request_data.version_key is not None else "v0"
        en = request_data.is_enabled if request_data.is_enabled is not None else True
        row = ModuleOverride(module_key=request_data.module_key, version_key=ver, is_enabled=en)
        db.add(row)
    if request_data.version_key is not None:
        row.version_key = request_data.version_key
    if request_data.is_enabled is not None:
        row.is_enabled = request_data.is_enabled
    row.updated_by = current_user.id
    row.reason = request_data.reason
    db.flush()

    after = {"module_key": row.module_key, "version_key": row.version_key, "is_enabled": row.is_enabled}
    append_switch_audit(
        db,
        actor_user_id=current_user.id,
        action_type="MODULE_OVERRIDE_SET",
        before=before,
        after=after,
        reason=request_data.reason,
    )
    db.commit()
    refresh_runtime_cache(db)
    return {"module_key": row.module_key, "version_key": row.version_key, "is_enabled": row.is_enabled}
