"""Admin security endpoints for freeze and runtime config."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import write_audit_critical
from app.core.dependencies import get_current_user, get_db, require_roles
from app.core.errors import get_request_id
from app.models.admin_security import AdminSecurityRuntime
from app.models.question_cms import AuditLog
from app.models.user import User, UserRole
from app.security.admin_freeze import check_admin_freeze, get_admin_freeze_config
from app.security.police_mode import validate_police_confirm

router = APIRouter(prefix="/admin/security", tags=["Admin - Security"])


# --- Schemas ---


class AdminFreezeRequest(BaseModel):
    """Request to set/unset admin freeze."""

    freeze: bool = Field(..., description="Enable or disable admin freeze")
    reason: str = Field(..., min_length=1, description="Reason for freeze change")
    confirmation_phrase: str = Field(..., description="Confirmation phrase: 'SET ADMIN FREEZE'")


class AdminSecurityRuntimeResponse(BaseModel):
    """Response for admin security runtime config."""

    admin_freeze: bool
    freeze_reason: str | None = None
    set_by_user_id: str | None = None
    set_at: str | None = None


# --- Endpoints ---


@router.get(
    "/runtime",
    response_model=AdminSecurityRuntimeResponse,
    summary="Get admin security runtime config",
    description="Get current admin freeze status.",
)
async def get_admin_security_runtime(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminSecurityRuntimeResponse:
    """Get admin security runtime configuration."""
    config = get_admin_freeze_config(db)

    return AdminSecurityRuntimeResponse(
        admin_freeze=config.admin_freeze,
        freeze_reason=config.freeze_reason,
        set_by_user_id=str(config.set_by_user_id) if config.set_by_user_id else None,
        set_at=config.set_at.isoformat() if config.set_at else None,
    )


@router.post(
    "/freeze",
    response_model=AdminSecurityRuntimeResponse,
    summary="Set admin freeze",
    description="Enable or disable admin freeze (read-only mode for mutations).",
)
async def set_admin_freeze(
    request_data: AdminFreezeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminSecurityRuntimeResponse:
    """Set or unset admin freeze."""
    # Validate police-mode confirmation
    reason = validate_police_confirm(
        request,
        request_data.confirmation_phrase,
        request_data.reason,
        "SET ADMIN FREEZE",
    )
    
    config = get_admin_freeze_config(db)
    
    # Update config
    old_freeze = config.admin_freeze
    config.admin_freeze = request_data.freeze
    config.freeze_reason = reason if request_data.freeze else None
    config.set_by_user_id = current_user.id
    config.set_at = datetime.now(UTC)
    
    db.commit()
    db.refresh(config)
    
    # Write audit log
    request_id = get_request_id(request)
    write_audit_critical(
        db=db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="ADMIN_FREEZE_CHANGED",
        entity_type="ADMIN_SECURITY",
        entity_id=uuid4(),  # Use a generated ID for singleton entity
        reason=reason,
        request=request,
        before={"admin_freeze": old_freeze},
        after={"admin_freeze": request_data.freeze, "reason": reason},
        meta={"request_id": request_id},
    )
    db.commit()
    
    return AdminSecurityRuntimeResponse(
        admin_freeze=config.admin_freeze,
        freeze_reason=config.freeze_reason,
        set_by_user_id=str(config.set_by_user_id) if config.set_by_user_id else None,
        set_at=config.set_at.isoformat() if config.set_at else None,
    )
