"""System flags model for runtime configuration."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class SystemFlag(Base):
    """System-wide runtime flags (source of truth for exam mode, etc.)."""

    __tablename__ = "system_flags"

    key = Column(String(100), primary_key=True, nullable=False)
    value = Column(Boolean, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, onupdate=func.now())
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=True)

    # Relationship
    updated_by_user = relationship("User", foreign_keys=[updated_by])
