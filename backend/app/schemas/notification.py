"""Notification schemas."""

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: str
    type: str  # SYSTEM|SECURITY|COURSE|REMINDER|ANNOUNCEMENT
    title: str
    body: str
    action_url: str | None = None
    severity: str  # info|warning|critical
    is_read: bool
    read_at: str | None = None  # ISO timestamp or null
    created_at: str  # ISO timestamp

    class Config:
        from_attributes = True


class NotificationsListResponse(BaseModel):
    """Notifications list response (paginated)."""

    items: list[NotificationResponse]
    page: int
    page_size: int
    total: int


class UnreadCountResponse(BaseModel):
    """Unread count response."""

    unread_count: int


class MarkAllReadResponse(BaseModel):
    """Mark all read response."""

    updated: int


class MarkReadResponse(BaseModel):
    """Mark single notification as read response."""

    id: str
    is_read: bool
