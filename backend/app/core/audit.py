"""Audit logging helpers."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.question_cms import AuditLog


def write_audit(
    db: Session,
    actor_user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditLog:
    """Write an audit log entry."""
    audit_entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        meta=meta,
    )
    db.add(audit_entry)
    return audit_entry
