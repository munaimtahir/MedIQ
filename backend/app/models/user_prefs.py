"""User learning preferences models."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserLearningPrefs(Base):
    """User learning preferences for spacing and revision."""

    __tablename__ = "user_learning_prefs"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    revision_daily_target = Column(Integer, nullable=True)  # Default from config
    spacing_multiplier = Column(Numeric(5, 2), nullable=False, server_default="1.0")  # 0.8 = more frequent, 1.2 = less frequent
    retention_target_override = Column(Numeric(5, 4), nullable=True)  # Optional override for desired_retention
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User")
