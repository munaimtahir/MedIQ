"""Admin system info endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import write_audit_critical
from app.core.config import settings
from app.core.dependencies import get_current_user, require_roles
from app.core.errors import get_request_id
from app.core.redis_client import is_redis_available
from app.db.session import get_db
from app.models.user import User, UserRole
from app.security.admin_freeze import check_admin_freeze
from app.security.police_mode import validate_police_confirm
from app.system.flags import (
    get_exam_mode_state,
    get_freeze_updates_state,
    get_flag,
    is_exam_mode,
    set_flag,
)

router = APIRouter(prefix="/admin/system", tags=["Admin - System"])


@router.get(
    "/info",
    summary="Get system information",
    description="Get system information for admin dashboard.",
)
async def get_system_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> dict:
    """Get system information."""
    # Check database connection
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        pass

    # Check Redis
    redis_connected = False
    if settings.REDIS_ENABLED:
        redis_connected = is_redis_available()

    return {
        "environment": settings.ENVIRONMENT if hasattr(settings, "ENVIRONMENT") else "development",
        "api_version": "v1",
        "backend_version": getattr(settings, "GIT_SHA", None) or "unknown",
        "db_connected": db_connected,
        "redis_connected": redis_connected if settings.REDIS_ENABLED else None,
    }


# ============================================================================
# Exam Mode Runtime Flag
# ============================================================================


class ExamModeStateResponse(BaseModel):
    """Exam mode state response."""

    enabled: bool
    updated_at: str | None
    updated_by: dict | None = None
    reason: str | None = None
    source: str  # "db" | "cache" | "fallback"


class ExamModeToggleRequest(BaseModel):
    """Request to toggle exam mode."""

    enabled: bool = Field(..., description="Enable or disable exam mode")
    reason: str = Field(..., description="Reason for the change (required)")
    confirmation_phrase: str = Field(..., description="Confirmation phrase: 'ENABLE EXAM MODE' or 'DISABLE EXAM MODE'")


@router.get("/exam-mode", response_model=ExamModeStateResponse)
def get_exam_mode(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ExamModeStateResponse:
    """Get current exam mode state."""
    state = get_exam_mode_state(db)
    
    # Resolve updated_by user if available
    updated_by_dict = None
    if state.get("updated_by"):
        try:
            user = db.query(User).filter(User.id == UUID(state["updated_by"])).first()
            if user:
                updated_by_dict = {
                    "id": str(user.id),
                    "email": user.email,
                }
        except Exception:
            pass  # Ignore errors resolving user
    
    return ExamModeStateResponse(
        enabled=state["enabled"],
        updated_at=state["updated_at"],
        updated_by=updated_by_dict,
        reason=state["reason"],
        source=state["source"],
    )


@router.post("/exam-mode", response_model=ExamModeStateResponse)
def toggle_exam_mode(
    request_data: ExamModeToggleRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ExamModeStateResponse:
    """Toggle exam mode (requires typed confirmation phrase)."""
    # Check admin freeze
    check_admin_freeze(db)
    
    # Validate confirmation phrase
    expected_phrase = "ENABLE EXAM MODE" if request_data.enabled else "DISABLE EXAM MODE"
    reason = validate_police_confirm(
        request,
        request_data.confirmation_phrase,
        request_data.reason,
        expected_phrase,
    )
    
    # Get current state
    current_flag = get_flag(db, "EXAM_MODE")
    before_state = {
        "enabled": current_flag.value if current_flag else False,
        "updated_at": current_flag.updated_at.isoformat() if current_flag and current_flag.updated_at else None,
        "updated_by": str(current_flag.updated_by) if current_flag and current_flag.updated_by else None,
        "reason": current_flag.reason if current_flag else None,
    }
    
    # Update flag
    updated_flag = set_flag(
        db=db,
        key="EXAM_MODE",
        value=request_data.enabled,
        updated_by=current_user.id,
        reason=reason,
    )
    
    # Write audit log
    from uuid import uuid4
    
    request_id = get_request_id(request)
    write_audit_critical(
        db=db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="EXAM_MODE_CHANGED",
        entity_type="SYSTEM_FLAG",
        entity_id=uuid4(),
        reason=reason,
        request=request,
        before=before_state,
        after={
            "enabled": updated_flag.value,
            "updated_at": updated_flag.updated_at.isoformat(),
            "updated_by": str(updated_flag.updated_by) if updated_flag.updated_by else None,
            "reason": updated_flag.reason,
        },
        meta={"request_id": request_id},
    )
    db.commit()

    # Return new state
    state = get_exam_mode_state(db)
    updated_by_dict = None
    if state.get("updated_by"):
        try:
            user = db.query(User).filter(User.id == UUID(state["updated_by"])).first()
            if user:
                updated_by_dict = {
                    "id": str(user.id),
                    "email": user.email,
                }
        except Exception:
            pass

    return ExamModeStateResponse(
        enabled=state["enabled"],
        updated_at=state["updated_at"],
        updated_by=updated_by_dict,
        reason=state["reason"],
        source=state["source"],
    )


# ============================================================================
# Freeze Updates Runtime Flag
# ============================================================================


class FreezeUpdatesStateResponse(BaseModel):
    """Freeze updates state response."""

    enabled: bool
    updated_at: str | None
    updated_by: dict | None = None
    reason: str | None = None
    source: str  # "db" | "cache" | "fallback"


class FreezeUpdatesToggleRequest(BaseModel):
    """Request to toggle freeze updates."""

    enabled: bool = Field(..., description="Enable or disable freeze updates")
    reason: str = Field(..., description="Reason for the change (required)")
    confirmation_phrase: str = Field(
        ...,
        description="Confirmation phrase: 'ENABLE FREEZE UPDATES' or 'DISABLE FREEZE UPDATES'",
    )


@router.get("/freeze-updates", response_model=FreezeUpdatesStateResponse)
def get_freeze_updates_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> FreezeUpdatesStateResponse:
    """Get current freeze-updates state."""
    state = get_freeze_updates_state(db)
    updated_by_dict = None
    if state.get("updated_by"):
        try:
            user = db.query(User).filter(User.id == UUID(state["updated_by"])).first()
            if user:
                updated_by_dict = {"id": str(user.id), "email": user.email}
        except Exception:
            pass
    return FreezeUpdatesStateResponse(
        enabled=state["enabled"],
        updated_at=state["updated_at"],
        updated_by=updated_by_dict,
        reason=state["reason"],
        source=state["source"],
    )


@router.post("/freeze-updates", response_model=FreezeUpdatesStateResponse)
def toggle_freeze_updates(
    request_data: FreezeUpdatesToggleRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> FreezeUpdatesStateResponse:
    """Toggle freeze updates (requires typed confirmation phrase)."""
    check_admin_freeze(db)
    expected_phrase = "ENABLE FREEZE UPDATES" if request_data.enabled else "DISABLE FREEZE UPDATES"
    reason = validate_police_confirm(
        request,
        request_data.confirmation_phrase,
        request_data.reason,
        expected_phrase,
    )
    from uuid import uuid4

    current_flag = get_flag(db, "FREEZE_UPDATES")
    before_state = {
        "enabled": current_flag.value if current_flag else False,
        "updated_at": current_flag.updated_at.isoformat() if current_flag and current_flag.updated_at else None,
        "updated_by": str(current_flag.updated_by) if current_flag and current_flag.updated_by else None,
        "reason": current_flag.reason if current_flag else None,
    }
    updated_flag = set_flag(
        db=db,
        key="FREEZE_UPDATES",
        value=request_data.enabled,
        updated_by=current_user.id,
        reason=reason,
    )
    request_id = get_request_id(request)
    write_audit_critical(
        db=db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="FREEZE_UPDATES_CHANGED",
        entity_type="SYSTEM_FLAG",
        entity_id=uuid4(),
        reason=reason,
        request=request,
        before=before_state,
        after={
            "enabled": updated_flag.value,
            "updated_at": updated_flag.updated_at.isoformat(),
            "updated_by": str(updated_flag.updated_by) if updated_flag.updated_by else None,
            "reason": updated_flag.reason,
        },
        meta={"request_id": request_id},
    )
    db.commit()
    state = get_freeze_updates_state(db)
    updated_by_dict = None
    if state.get("updated_by"):
        try:
            user = db.query(User).filter(User.id == UUID(state["updated_by"])).first()
            if user:
                updated_by_dict = {"id": str(user.id), "email": user.email}
        except Exception:
            pass
    return FreezeUpdatesStateResponse(
        enabled=state["enabled"],
        updated_at=state["updated_at"],
        updated_by=updated_by_dict,
        reason=state["reason"],
        source=state["source"],
    )
