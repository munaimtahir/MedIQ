"""Append-only switch audit log for runtime control actions."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.runtime_control import SwitchAuditLog


def append_switch_audit(
    db: Session,
    *,
    actor_user_id: uuid.UUID | None,
    action_type: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
) -> SwitchAuditLog:
    """Append an immutable audit record. Does not commit."""
    row = SwitchAuditLog(
        id=uuid.uuid4(),
        actor_user_id=actor_user_id,
        action_type=action_type,
        before=before,
        after=after,
        reason=reason,
    )
    db.add(row)
    return row
