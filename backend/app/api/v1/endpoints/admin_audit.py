"""Admin audit log endpoints (dev-only)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.question_cms import AuditLog
from app.models.user import User, UserRole
from pydantic import BaseModel

router = APIRouter(prefix="/admin/audit", tags=["Admin - Audit"])


class AuditLogOut(BaseModel):
    """Audit log entry response."""

    id: UUID
    actor_user_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    before: dict | None
    after: dict | None
    meta: dict | None
    created_at: str

    class Config:
        from_attributes = True


@router.get(
    "",
    response_model=list[AuditLogOut],
    summary="Query audit log (dev-only)",
    description="Query audit log entries. Only available in dev environment.",
)
async def query_audit_log(
    entity_type: Annotated[str | None, Query(description="Filter by entity type")] = None,
    entity_id: Annotated[UUID | None, Query(description="Filter by entity ID")] = None,
    action: Annotated[str | None, Query(description="Filter by action")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results")] = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[AuditLogOut]:
    """Query audit log entries (dev-only endpoint)."""
    if settings.ENV != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit log query endpoint is only available in dev environment",
        )

    query = db.query(AuditLog)

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))

    entries = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

    return [AuditLogOut.model_validate(entry) for entry in entries]
