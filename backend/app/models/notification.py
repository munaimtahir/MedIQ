"""Notification model."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class NotificationType(str, Enum):
    """Notification type enum."""

    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
    COURSE = "COURSE"
    REMINDER = "REMINDER"
    ANNOUNCEMENT = "ANNOUNCEMENT"


class NotificationSeverity(str, Enum):
    """Notification severity enum."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Notification(Base):
    """Notification model for user notifications."""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String, nullable=False)  # NotificationType enum values
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    action_url = Column(Text, nullable=True)
    severity = Column(String, nullable=False, server_default="info")  # NotificationSeverity enum values
    is_read = Column(Boolean, nullable=False, server_default="false")
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    user = relationship("User", backref="notifications")

    __table_args__ = (
        Index("ix_notifications_user_created_at", "user_id", "created_at"),
        Index("ix_notifications_user_is_read_created_at", "user_id", "is_read", "created_at"),
    )
