"""Audit logging helpers."""

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.errors import get_request_id
from app.models.question_cms import AuditLog
from app.security.critical_actions import is_critical_action


def write_audit(
    db: Session,
    actor_user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    actor_role: str | None = None,
    request: Request | None = None,
    reason: str | None = None,
) -> AuditLog:
    """
    Write an audit log entry.
    
    Args:
        db: Database session
        actor_user_id: User ID performing the action
        action: Action type (e.g., "EMAIL_MODE_SWITCH")
        entity_type: Type of entity (e.g., "EMAIL_RUNTIME")
        entity_id: ID of the entity
        before: State before change
        after: State after change
        meta: Additional metadata
        actor_role: Role of the actor (extracted from user if not provided)
        request: FastAPI request (for request_id and police_reason)
        reason: Reason for the action (required for critical actions)
    """
    # Build meta dict with standard fields
    audit_meta = meta.copy() if meta else {}
    
    # Add request_id if available
    if request:
        request_id = get_request_id(request)
        audit_meta["request_id"] = request_id
        
        # Add police-mode reason if available
        police_reason = getattr(request.state, "police_reason", None)
        if police_reason:
            audit_meta["police_reason"] = police_reason
    
    # Add reason (from parameter or police_reason)
    if reason:
        audit_meta["reason"] = reason
    elif request and hasattr(request.state, "police_reason"):
        audit_meta["reason"] = request.state.police_reason
    
    # Add actor_role
    if actor_role:
        audit_meta["actor_role"] = actor_role
    
    # For critical actions, reason is required
    if is_critical_action(action) and not audit_meta.get("reason"):
        raise ValueError(f"Reason is required for critical action: {action}")
    
    audit_entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        meta=audit_meta,
    )
    db.add(audit_entry)
    return audit_entry


def write_audit_critical(
    db: Session,
    actor_user_id: UUID,
    actor_role: str,
    action: str,
    entity_type: str,
    entity_id: UUID,
    reason: str,
    request: Request | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditLog:
    """
    Write an audit log entry for a critical action.
    
    This is a convenience function that ensures all required fields are present.
    """
    return write_audit(
        db=db,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        meta=meta,
        actor_role=actor_role,
        request=request,
        reason=reason,
    )
