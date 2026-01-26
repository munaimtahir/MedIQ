"""Admin notification broadcast endpoints."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.pagination import PaginatedResponse, PaginationParams, pagination_params
from app.core.dependencies import require_roles
from app.security.exam_mode_gate import require_not_exam_mode
from app.security.rate_limit import create_user_rate_limit_dep
from app.db.session import get_db
from app.models.academic import UserBlock, UserProfile
from app.models.notification import Notification
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin/notifications", tags=["Admin - Notifications"])


# ============================================================================
# Broadcast
# ============================================================================


class NotificationData(BaseModel):
    """Notification data for broadcast."""

    type: str = Field(..., description="Notification type: SYSTEM|SECURITY|COURSE|REMINDER|ANNOUNCEMENT")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    action_url: str | None = Field(None, description="Optional action URL")
    severity: str = Field(default="info", description="Severity: info|warning|critical")


class BroadcastTarget(BaseModel):
    """Broadcast target specification."""

    mode: str = Field(..., description="Target mode: user_ids|year|block|cohort_filter")
    user_ids: list[UUID] | None = Field(None, description="Direct user IDs (for mode=user_ids)")
    year: int | None = Field(None, description="Academic year ID (for mode=year)")
    block_ids: list[int] | None = Field(None, description="Block IDs (for mode=block)")
    cohort_id: str | None = Field(None, description="Cohort identifier (for mode=cohort_filter)")


class BroadcastRequest(BaseModel):
    """Broadcast notification request."""

    target: BroadcastTarget
    notification: NotificationData
    reason: str = Field(..., description="Reason for broadcast")
    confirmation_phrase: str = Field(..., description="Confirmation phrase: 'BROADCAST NOTIFICATION'")


class BroadcastResponse(BaseModel):
    """Broadcast response."""

    created: int
    target_summary: dict[str, Any]  # Changed from target_stats to target_summary for consistency


def resolve_user_ids_from_target(
    db: Session,
    target: BroadcastTarget,
) -> list[UUID]:
    """
    Resolve user IDs from target filter.

    Args:
        db: Database session
        target: Broadcast target specification

    Returns:
        List of user IDs
    """
    if target.mode == "user_ids":
        if not target.user_ids:
            return []
        # Validate that users exist and are active
        users = db.query(User.id).filter(User.id.in_(target.user_ids), User.is_active == True).all()  # noqa: E712
        return [user.id for user in users]

    elif target.mode == "year":
        if not target.year:
            return []
        # Get users by academic year via UserProfile
        stmt = (
            select(User.id)
            .join(UserProfile, User.id == UserProfile.user_id)
            .where(UserProfile.selected_year_id == target.year, User.is_active == True)  # noqa: E712
        )
        result = db.execute(stmt)
        return [row[0] for row in result.all()]

    elif target.mode == "block":
        if not target.block_ids:
            return []
        # Get users by block IDs via UserBlock
        stmt = (
            select(User.id)
            .join(UserProfile, User.id == UserProfile.user_id)
            .join(UserBlock, UserProfile.user_id == UserBlock.user_id)
            .where(
                UserBlock.block_id.in_(target.block_ids),
                User.is_active == True,  # noqa: E712
            )
        )
        result = db.execute(stmt)
        return [row[0] for row in result.all()]

    elif target.mode == "cohort_filter":
        # For now, cohort_filter is a placeholder - can be extended later
        # For MVP, treat it as an empty filter (no users)
        # In production, this could query a cohort table or use a more complex filter
        return []

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target mode: {target.mode}",
        )


@router.post(
    "/broadcast",
    response_model=BroadcastResponse,
    dependencies=[
        Depends(create_user_rate_limit_dep("admin.notifications_broadcast", fail_open=False)),
        Depends(require_not_exam_mode("notification_broadcast")),
    ],
)
def broadcast_notification(
    request_data: BroadcastRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> BroadcastResponse:
    """
    Broadcast notification to multiple users (bulk insert).

    Requires confirmation phrase and reason for audit.
    **Blocked**: When exam mode is enabled (423 Locked)
    """
    
    # Check admin freeze
    check_admin_freeze(db)
    
    # Validate police-mode confirmation
    reason = validate_police_confirm(
        http_request,
        request_data.confirmation_phrase,
        request_data.reason,
        "BROADCAST NOTIFICATION",
    )

    # Resolve user IDs from target
    user_ids = resolve_user_ids_from_target(db, request_data.target)

    if not user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No users found matching the target criteria",
        )

    # Bulk insert notifications in chunks of 1000
    chunk_size = 1000
    total_created = 0

    for i in range(0, len(user_ids), chunk_size):
        chunk = user_ids[i : i + chunk_size]
        notifications = [
            Notification(
                user_id=user_id,
                type=request_data.notification.type,
                title=request_data.notification.title,
                body=request_data.notification.body,
                action_url=request_data.notification.action_url,
                severity=request_data.notification.severity,
                is_read=False,
            )
            for user_id in chunk
        ]
        db.bulk_save_objects(notifications)
        total_created += len(notifications)

    db.commit()

    # Write audit log
    from uuid import uuid4 as gen_uuid
    
    request_id = get_request_id(http_request) or str(gen_uuid())
    write_audit_critical(
        db=db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="NOTIFICATION_BROADCAST",
        entity_type="notification",
        entity_id=gen_uuid(),  # Generate a UUID for the broadcast event itself
        reason=reason,
        request=http_request,
        after={
            "target_mode": request_data.target.mode,
            "user_count": total_created,
            "notification_type": request_data.notification.type,
            "severity": request_data.notification.severity,
            "title": request_data.notification.title,  # Store title for recent broadcasts
            "body": request_data.notification.body[:500],  # Store body snippet (first 500 chars)
        },
        meta={
            "request_id": request_id,
            "target_year": request_data.target.year,
            "target_block_ids": request_data.target.block_ids,
            "target_cohort_id": request_data.target.cohort_id,
            "action_url": request_data.notification.action_url,
        },
    )
    db.commit()

    # Build target summary
    target_summary = {
        "resolved_users": total_created,
        "mode": request_data.target.mode,
    }
    if request_data.target.year:
        target_summary["year"] = request_data.target.year
    if request_data.target.block_ids:
        target_summary["blocks"] = request_data.target.block_ids
    if request_data.target.cohort_id:
        target_summary["cohort_id"] = request_data.target.cohort_id

    return BroadcastResponse(
        created=total_created,
        target_summary=target_summary,
    )


# ============================================================================
# Recent Broadcasts
# ============================================================================


class BroadcastSummaryItem(BaseModel):
    """Broadcast summary for recent broadcasts list."""

    id: UUID
    title: str
    type: str
    severity: str
    created_at: str
    created_by: UUID | None
    target_summary: dict[str, Any]


class BroadcastDetailItem(BaseModel):
    """Full broadcast details including audit metadata."""

    id: UUID
    title: str
    type: str
    severity: str
    body: str  # Full body snippet from audit log
    action_url: str | None
    created_at: str
    created_by: UUID | None
    target_summary: dict[str, Any]
    audit_metadata: dict[str, Any]  # Full audit log data (before, after, meta)


@router.get("/recent", response_model=PaginatedResponse[BroadcastSummaryItem])
def list_recent_broadcasts(
    pagination: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> PaginatedResponse[BroadcastSummaryItem]:
    """
    List recent notification broadcasts (from audit log).

    This queries AuditLog for NOTIFICATION_BROADCAST actions.
    """
    try:
        from app.models.question_cms import AuditLog

        # Query audit log for notification broadcasts
        query = (
            db.query(AuditLog)
            .filter(AuditLog.action == "NOTIFICATION_BROADCAST")
            .order_by(AuditLog.created_at.desc())
        )

        total = query.count()
        items = query.offset(pagination.offset).limit(pagination.page_size).all()

        # Transform audit log entries to broadcast summaries
        broadcast_items = []
        for audit_item in items:
            after_data = audit_item.after or {}
            meta_data = audit_item.meta or {}
            target_summary = {
                "mode": after_data.get("target_mode", "unknown"),
                "user_count": after_data.get("user_count", 0),
                "year": meta_data.get("target_year"),
                "block_ids": meta_data.get("target_block_ids", []),
            }

            # Extract notification details from audit log
            # Title and body are now stored in after_data
            broadcast_items.append(
                BroadcastSummaryItem(
                    id=audit_item.id,
                    title=after_data.get("title", "Notification Broadcast"),
                    type=after_data.get("notification_type", "ANNOUNCEMENT"),
                    severity=after_data.get("severity", "info"),
                    created_at=audit_item.created_at.isoformat(),
                    created_by=audit_item.actor_user_id,
                    target_summary=target_summary,
                )
            )

        return PaginatedResponse(
            items=broadcast_items,
            page=pagination.page,
            page_size=pagination.page_size,
            total=total,
        )
    except ImportError:
        # AuditLog not available, return empty
        return PaginatedResponse(
            items=[],
            page=pagination.page,
            page_size=pagination.page_size,
            total=0,
        )


@router.get("/recent/{broadcast_id}", response_model=BroadcastDetailItem)
def get_broadcast_detail(
    broadcast_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> BroadcastDetailItem:
    """
    Get full details of a specific broadcast notification (including audit metadata).
    """
    try:
        from app.models.question_cms import AuditLog

        # Query audit log for the specific broadcast
        audit_item = (
            db.query(AuditLog)
            .filter(
                AuditLog.id == broadcast_id,
                AuditLog.action == "NOTIFICATION_BROADCAST",
            )
            .first()
        )

        if not audit_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Broadcast with ID {broadcast_id} not found",
            )

        after_data = audit_item.after or {}
        meta_data = audit_item.meta or {}
        target_summary = {
            "mode": after_data.get("target_mode", "unknown"),
            "user_count": after_data.get("user_count", 0),
            "year": meta_data.get("target_year"),
            "block_ids": meta_data.get("target_block_ids", []),
            "cohort_id": meta_data.get("target_cohort_id"),
        }

        return BroadcastDetailItem(
            id=audit_item.id,
            title=after_data.get("title", "Notification Broadcast"),
            type=after_data.get("notification_type", "ANNOUNCEMENT"),
            severity=after_data.get("severity", "info"),
            body=after_data.get("body", ""),  # Body snippet (first 500 chars)
            action_url=meta_data.get("action_url"),
            created_at=audit_item.created_at.isoformat(),
            created_by=audit_item.actor_user_id,
            target_summary=target_summary,
            audit_metadata={
                "before": audit_item.before,
                "after": audit_item.after,
                "meta": audit_item.meta,
                "reason": meta_data.get("reason"),
            },
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit log not available",
        )
