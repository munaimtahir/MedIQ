"""Admin email runtime and outbox endpoints."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.common.pagination import PaginatedResponse, PaginationParams, pagination_params
from app.core.audit import write_audit_critical
from app.core.dependencies import require_roles
from app.core.errors import get_request_id
from app.security.admin_freeze import check_admin_freeze
from app.security.exam_mode_gate import require_not_exam_mode
from app.security.police_mode import validate_police_confirm
from app.security.rate_limit import create_user_rate_limit_dep
from app.db.session import get_db
from app.email.provider_factory import get_email_provider
from app.email.runtime import (
    EmailMode,
    EmailRuntimeConfigData,
    get_effective_email_mode,
    get_email_runtime_config_sync,
)
from app.email.service import drain_outbox
from app.models.email import EmailOutbox, EmailRuntimeConfig, EmailStatus, EmailSwitchEvent
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin/email", tags=["Admin - Email"])


# ============================================================================
# Runtime Configuration
# ============================================================================


class EmailRuntimeResponse(BaseModel):
    """Email runtime configuration response."""

    requested_mode: str
    effective_mode: str
    freeze: bool
    provider: dict[str, bool | str]
    warnings: list[str]
    blocking_reasons: list[str]


class EmailModeSwitchRequest(BaseModel):
    """Request to switch email mode."""

    mode: str = Field(..., description="Email mode: disabled|shadow|active")
    reason: str = Field(..., description="Reason for the switch")
    confirmation_phrase: str = Field(..., description="Confirmation phrase (e.g., 'SWITCH EMAIL TO ACTIVE')")


@router.get("/runtime", response_model=EmailRuntimeResponse)
def get_email_runtime(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> EmailRuntimeResponse:
    """Get current email runtime configuration."""
    runtime_cfg = get_email_runtime_config_sync(db)
    provider, provider_configured = get_email_provider()

    effective_mode, warnings, blocking_reasons = get_effective_email_mode(
        requested_mode=runtime_cfg.requested_mode,
        email_freeze=runtime_cfg.email_freeze,
        provider_configured=provider_configured,
    )

    provider_type = "none"
    if provider:
        provider_type = provider.__class__.__name__.replace("EmailProvider", "").lower()

    return EmailRuntimeResponse(
        requested_mode=runtime_cfg.requested_mode.value,
        effective_mode=effective_mode.value,
        freeze=runtime_cfg.email_freeze,
        provider={"type": provider_type, "configured": provider_configured},
        warnings=warnings,
        blocking_reasons=blocking_reasons,
    )


@router.post("/runtime/switch", response_model=EmailRuntimeResponse)
def switch_email_mode(
    request_data: EmailModeSwitchRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> EmailRuntimeResponse:
    """Switch email runtime mode (requires typed confirmation phrase)."""
    # Check admin freeze
    check_admin_freeze(db)
    
    # Validate mode
    try:
        new_mode = EmailMode(request_data.mode.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode: {request_data.mode}. Must be one of: disabled, shadow, active",
        )

    # Validate police-mode confirmation
    expected_phrases = {
        EmailMode.DISABLED: "SWITCH EMAIL TO DISABLED",
        EmailMode.SHADOW: "SWITCH EMAIL TO SHADOW",
        EmailMode.ACTIVE: "SWITCH EMAIL TO ACTIVE",
    }
    expected = expected_phrases[new_mode]
    reason = validate_police_confirm(
        request,
        request_data.confirmation_phrase,
        request_data.reason,
        expected,
    )

    # Get current config
    current_config = get_email_runtime_config_sync(db)
    config = db.query(EmailRuntimeConfig).first()
    if not config:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Email runtime config not found")

    # Create audit event
    previous_config = {
        "requested_mode": current_config.requested_mode.value,
        "email_freeze": current_config.email_freeze,
    }
    new_config = {
        "requested_mode": new_mode.value,
        "email_freeze": config.email_freeze,  # Freeze state unchanged unless explicitly set
    }

    switch_event = EmailSwitchEvent(
        previous_config=previous_config,
        new_config=new_config,
        reason=reason,
        created_by_user_id=current_user.id,
    )
    db.add(switch_event)
    
    # Write audit log
    from uuid import uuid4
    
    request_id = get_request_id(request)
    write_audit_critical(
        db=db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="EMAIL_MODE_SWITCH",
        entity_type="EMAIL_RUNTIME",
        entity_id=uuid4(),
        reason=reason,
        request=request,
        before=previous_config,
        after=new_config,
        meta={"request_id": request_id},
    )

    # Update config
    config.requested_mode = new_mode.value
    config.reason = reason
    config.changed_by_user_id = current_user.id
    db.commit()
    db.refresh(config)

    # Return updated config
    updated_cfg = get_email_runtime_config_sync(db)
    provider, provider_configured = get_email_provider()

    effective_mode, warnings, blocking_reasons = get_effective_email_mode(
        requested_mode=updated_cfg.requested_mode,
        email_freeze=updated_cfg.email_freeze,
        provider_configured=provider_configured,
    )

    provider_type = "none"
    if provider:
        provider_type = provider.__class__.__name__.replace("EmailProvider", "").lower()

    # Effective mode change is logged via EmailSwitchEvent

    return EmailRuntimeResponse(
        requested_mode=updated_cfg.requested_mode.value,
        effective_mode=effective_mode.value,
        freeze=updated_cfg.email_freeze,
        provider={"type": provider_type, "configured": provider_configured},
        warnings=warnings,
        blocking_reasons=blocking_reasons,
    )


# ============================================================================
# Outbox Management
# ============================================================================


class EmailOutboxItem(BaseModel):
    """Email outbox item response (list view - minimal fields)."""

    id: UUID
    to_email: str
    to_name: str | None
    subject: str
    template_key: str
    status: str
    provider: str | None
    provider_message_id: str | None
    attempts: int
    last_error: str | None
    created_at: str
    updated_at: str
    sent_at: str | None


class EmailOutboxDetail(BaseModel):
    """Email outbox item detail (full record)."""

    id: UUID
    to_email: str
    to_name: str | None
    subject: str
    body_text: str | None
    body_html: str | None
    template_key: str
    template_vars: dict[str, Any]
    status: str
    provider: str | None
    provider_message_id: str | None
    attempts: int
    last_error: str | None
    created_at: str
    updated_at: str
    sent_at: str | None


class DrainOutboxRequest(BaseModel):
    """Request to drain email outbox."""

    limit: int = Field(default=50, ge=1, le=500, description="Maximum emails to process")
    reason: str = Field(..., description="Reason for manual drain")
    confirmation_phrase: str = Field(..., description="Confirmation phrase: 'DRAIN EMAIL OUTBOX'")


class DrainOutboxResponse(BaseModel):
    """Drain outbox response."""

    attempted: int
    sent: int
    failed: int
    skipped: int
    effective_mode: str


@router.get("/outbox", response_model=PaginatedResponse[EmailOutboxItem])
def list_outbox(
    status: str | None = Query(None, description="Filter by status"),
    pagination: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> PaginatedResponse[EmailOutboxItem]:
    """List email outbox items."""
    query = db.query(EmailOutbox)

    if status:
        query = query.filter(EmailOutbox.status == status)

    total = query.count()
    items = query.order_by(EmailOutbox.created_at.desc()).offset(pagination.offset).limit(pagination.page_size).all()

    return PaginatedResponse(
        items=[
            EmailOutboxItem(
                id=item.id,
                to_email=item.to_email,
                to_name=item.to_name,
                subject=item.subject,
                template_key=item.template_key,
                status=item.status,
                provider=item.provider,
                provider_message_id=item.provider_message_id,
                attempts=item.attempts,
                last_error=item.last_error,
                created_at=item.created_at.isoformat(),
                updated_at=item.updated_at.isoformat(),
                sent_at=item.sent_at.isoformat() if item.sent_at else None,
            )
            for item in items
        ],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get("/outbox/{outbox_id}", response_model=EmailOutboxDetail)
def get_outbox_item(
    outbox_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> EmailOutboxDetail:
    """Get email outbox item by ID (full record with body content)."""
    item = db.query(EmailOutbox).filter(EmailOutbox.id == outbox_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email outbox item not found")

    # Truncate body content to safe max (50k chars) to prevent huge payloads
    MAX_BODY_LENGTH = 50_000
    body_text = item.body_text
    body_html = item.body_html
    if body_text and len(body_text) > MAX_BODY_LENGTH:
        body_text = body_text[:MAX_BODY_LENGTH] + "\n\n[Truncated - original length: {} chars]".format(len(item.body_text))
    if body_html and len(body_html) > MAX_BODY_LENGTH:
        body_html = body_html[:MAX_BODY_LENGTH] + "\n\n[Truncated - original length: {} chars]".format(len(item.body_html))

    return EmailOutboxDetail(
        id=item.id,
        to_email=item.to_email,
        to_name=item.to_name,
        subject=item.subject,
        body_text=body_text,
        body_html=body_html,
        template_key=item.template_key,
        template_vars=item.template_vars or {},
        status=item.status,
        provider=item.provider,
        provider_message_id=item.provider_message_id,
        attempts=item.attempts,
        last_error=item.last_error,
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
        sent_at=item.sent_at.isoformat() if item.sent_at else None,
    )


@router.post(
    "/outbox/drain",
    response_model=DrainOutboxResponse,
    dependencies=[
        Depends(create_user_rate_limit_dep("admin.email_drain", fail_open=False)),
        Depends(require_not_exam_mode("email_outbox_drain")),
    ],
)
def drain_outbox_endpoint(
    request_data: DrainOutboxRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> DrainOutboxResponse:
    """Manually drain email outbox (ADMIN only, requires confirmation phrase)."""
    
    # Check admin freeze
    check_admin_freeze(db)
    
    # Validate police-mode confirmation
    reason = validate_police_confirm(
        request,
        request_data.confirmation_phrase,
        request_data.reason,
        "DRAIN EMAIL OUTBOX",
    )

    # Drain outbox
    result = drain_outbox(db, limit=request_data.limit)
    
    # Write audit log
    from app.core.errors import get_request_id
    from uuid import uuid4
    
    request_id = get_request_id(request)
    write_audit_critical(
        db=db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="EMAIL_OUTBOX_DRAIN",
        entity_type="EMAIL_OUTBOX",
        entity_id=uuid4(),  # Use generated ID for operation
        reason=reason,
        request=request,
        after={"attempted": result["attempted"], "sent": result["sent"], "failed": result["failed"]},
        meta={"request_id": request_id, "limit": request_data.limit},
    )
    db.commit()

    return DrainOutboxResponse(
        attempted=result["attempted"],
        sent=result["sent"],
        failed=result["failed"],
        skipped=result["skipped"],
        effective_mode=result["effective_mode"],
    )
