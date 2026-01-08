"""Platform settings model."""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class PlatformSettings(Base):
    """Platform-wide settings stored as JSONB."""

    __tablename__ = "platform_settings"

    id = Column(Integer, primary_key=True, default=1, server_default="1")  # Singleton
    data = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationship
    updated_by = relationship("User", foreign_keys=[updated_by_user_id])
