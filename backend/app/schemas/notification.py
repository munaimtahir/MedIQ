"""Notification schemas."""

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: str
    type: str  # "announcement" | "system" | "reminder"
    title: str
    body: str
    created_at: str  # ISO timestamp
    read_at: str | None = None  # ISO timestamp or null

    class Config:
        from_attributes = True


class NotificationsListResponse(BaseModel):
    """Notifications list response."""

    items: list[NotificationResponse]


class MarkAllReadResponse(BaseModel):
    """Mark all read response."""

    updated: int
