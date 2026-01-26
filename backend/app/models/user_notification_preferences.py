"""User notification preferences model."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserNotificationPreferences(Base):
    """User notification preferences (future-proof)."""

    __tablename__ = "user_notification_preferences"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    email_opt_in = Column(Boolean, nullable=False, server_default="true")
    push_opt_in = Column(Boolean, nullable=False, server_default="false")
    digest_frequency = Column(String, nullable=False, server_default="off")  # off|daily|weekly
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="notification_preferences")
