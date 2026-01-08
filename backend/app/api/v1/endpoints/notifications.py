"""Notification endpoints for students."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    MarkAllReadResponse,
    NotificationResponse,
    NotificationsListResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "/me",
    response_model=NotificationsListResponse,
    summary="Get user notifications",
    description="Get the current user's notifications, ordered by created_at desc.",
)
async def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationsListResponse:
    """
    Retrieve the current user's notifications.
    Returns latest 50 notifications ordered by created_at desc.
    """
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    items = [
        NotificationResponse(
            id=str(n.id),
            type=n.type,
            title=n.title,
            body=n.body,
            created_at=n.created_at.isoformat(),
            read_at=n.read_at.isoformat() if n.read_at else None,
        )
        for n in notifications
    ]

    return NotificationsListResponse(items=items)


@router.post(
    "/me/mark-all-read",
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
    now = datetime.now(timezone.utc)

    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
        .update({"read_at": now}, synchronize_session=False)
    )

    db.commit()

    return MarkAllReadResponse(updated=updated)
