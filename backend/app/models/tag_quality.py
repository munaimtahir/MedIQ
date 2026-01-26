"""Tag quality debt logging models."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class TagQualityDebtLog(Base):
    """Log of tag quality debt (missing/inconsistent concept mappings)."""

    __tablename__ = "tag_quality_debt_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    theme_id = Column(
        Integer,
        ForeignKey("themes.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    reason = Column(String(50), nullable=False)  # MISSING_CONCEPT, MULTIPLE_CONCEPTS, INCONSISTENT_TAGS
    count = Column(Integer, nullable=False, server_default="1")

    # Relationships
    question = relationship("Question")
    theme = relationship("Theme")

    __table_args__ = (
        Index("ix_tag_quality_debt_log_occurred_at", "occurred_at"),
        Index("ix_tag_quality_debt_log_reason", "reason"),
        Index("ix_tag_quality_debt_log_theme_id", "theme_id"),
    )
