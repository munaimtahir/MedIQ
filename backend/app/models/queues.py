"""Revision queue aggregation and statistics models."""

import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class RevisionQueueTheme(Base):
    """Theme-level revision queue aggregation."""

    __tablename__ = "revision_queue_theme"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    theme_id = Column(
        Integer,  # Themes use Integer IDs, not UUIDs
        ForeignKey("themes.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    due_count_today = Column(Integer, nullable=False, server_default="0")
    overdue_count = Column(Integer, nullable=False, server_default="0")
    next_due_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User")
    theme = relationship("Theme")

    __table_args__ = (
        Index("ix_revision_queue_theme_user_due", "user_id", "due_count_today"),
    )


class RevisionQueueUserSummary(Base):
    """User-level revision queue summary."""

    __tablename__ = "revision_queue_user_summary"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    due_today_total = Column(Integer, nullable=False, server_default="0")
    overdue_total = Column(Integer, nullable=False, server_default="0")
    due_tomorrow_total = Column(Integer, nullable=False, server_default="0")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User")


class QueueStatsDaily(Base):
    """Daily queue statistics snapshots."""

    __tablename__ = "queue_stats_daily"

    date = Column(Date(), primary_key=True)
    due_today_total = Column(Integer, nullable=False, server_default="0")
    overdue_total = Column(Integer, nullable=False, server_default="0")
    due_tomorrow_total = Column(Integer, nullable=False, server_default="0")
    users_with_due = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
