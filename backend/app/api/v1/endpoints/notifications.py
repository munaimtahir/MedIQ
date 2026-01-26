"""Notification endpoints for students."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.common.pagination import PaginationParams, PaginatedResponse, pagination_params
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    MarkAllReadResponse,
    MarkReadResponse,
    NotificationResponse,
    NotificationsListResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "/",
    response_model=PaginatedResponse[NotificationResponse],
    summary="Get user notifications",
    description="Get the current user's notifications with pagination.",
)
async def get_notifications(
    unread_only: bool = Query(False, description="Filter to unread notifications only"),
    pagination: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[NotificationResponse]:
    """
    Retrieve the current user's notifications with pagination.
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)  # noqa: E712

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    notifications = (
        query.order_by(Notification.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )

    items = [
        NotificationResponse(
            id=str(n.id),
            type=n.type,
            title=n.title,
            body=n.body,
            action_url=n.action_url,
            severity=n.severity,
            is_read=n.is_read,
            read_at=n.read_at.isoformat() if n.read_at else None,
            created_at=n.created_at.isoformat(),
        )
        for n in notifications
    ]

    return PaginatedResponse(
        items=items,
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
    description="Get the count of unread notifications for the current user.",
)
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadCountResponse:
    """
    Get the count of unread notifications for the current user.
    """
    unread_count = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
        .scalar()
        or 0
    )

    return UnreadCountResponse(unread_count=unread_count)


@router.post(
    "/{notification_id}/read",
    response_model=MarkReadResponse,
    summary="Mark notification as read",
    description="Mark a specific notification as read (idempotent).",
)
async def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkReadResponse:
    """
    Mark a specific notification as read (idempotent).
    """
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    # Idempotent: only update if not already read
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)

    return MarkReadResponse(id=str(notification.id), is_read=notification.is_read)


@router.post(
    "/read-all",
    response_model=MarkAllReadResponse,
    summary="Mark all notifications as read",
    description="Mark all unread notifications for the current user as read.",
)
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkAllReadResponse:
    """
    Mark all unread notifications for the current user as read.
    """
    now = datetime.now(UTC)

    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .update({"is_read": True, "read_at": now}, synchronize_session=False)
    )

    db.commit()

    return MarkAllReadResponse(updated=updated)
