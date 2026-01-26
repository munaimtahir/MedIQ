"""Admin security runtime configuration model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AdminSecurityRuntime(Base):
    """Admin security runtime configuration (singleton)."""

    __tablename__ = "admin_security_runtime"

    id = Column(Integer, primary_key=True, default=1, server_default="1")  # Singleton
    admin_freeze = Column(Boolean, nullable=False, default=False)
    freeze_reason = Column(Text, nullable=True)
    set_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    set_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship
    set_by_user = relationship("User", foreign_keys=[set_by_user_id])
