"""Notification schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: str
    type: str  # "announcement" | "system" | "reminder"
    title: str
    body: str
    created_at: str  # ISO timestamp
    read_at: Optional[str] = None  # ISO timestamp or null

    class Config:
        from_attributes = True


class NotificationsListResponse(BaseModel):
    """Notifications list response."""

    items: list[NotificationResponse]


class MarkAllReadResponse(BaseModel):
    """Mark all read response."""

    updated: int
