"""Admin audit log endpoints (dev-only)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.common.pagination import PaginatedResponse, PaginationParams, pagination_params
from app.core.config import settings
from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.question_cms import AuditLog
from app.models.user import User, UserRole

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
    response_model=PaginatedResponse[AuditLogOut],
    summary="Query audit log (dev-only)",
    description="Query audit log entries. Only available in dev environment.",
)
async def query_audit_log(
    entity_type: Annotated[str | None, Query(description="Filter by entity type")] = None,
    entity_id: Annotated[UUID | None, Query(description="Filter by entity ID")] = None,
    action: Annotated[str | None, Query(description="Filter by action")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> PaginatedResponse[AuditLogOut]:
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

    query = query.order_by(AuditLog.created_at.desc())
    total = query.count()
    entries = query.offset(pagination.offset).limit(pagination.page_size).all()

    return PaginatedResponse(
        items=[AuditLogOut.model_validate(entry) for entry in entries],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )
