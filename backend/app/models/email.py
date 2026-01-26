"""Email outbox and runtime configuration models."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class EmailStatus(str, Enum):
    """Email outbox status."""

    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    BLOCKED_DISABLED = "blocked_disabled"
    BLOCKED_FROZEN = "blocked_frozen"
    SHADOW_LOGGED = "shadow_logged"


class EmailMode(str, Enum):
    """Email runtime mode."""

    DISABLED = "disabled"
    SHADOW = "shadow"
    ACTIVE = "active"


class EmailOutbox(Base):
    """Email outbox - provider-agnostic email queue."""

    __tablename__ = "email_outbox"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    to_email = Column(Text, nullable=False)
    to_name = Column(Text, nullable=True)
    subject = Column(Text, nullable=False)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    template_key = Column(Text, nullable=False)
    template_vars = Column(JSONB, nullable=False, server_default="{}")
    status = Column(Text, nullable=False)  # EmailStatus enum values
    provider = Column(Text, nullable=True)  # smtp|sendgrid|ses|none|console
    provider_message_id = Column(Text, nullable=True)
    attempts = Column(Integer, nullable=False, server_default="0")
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_email_outbox_status_created_at", "status", "created_at"),
        Index("ix_email_outbox_to_email_created_at", "to_email", "created_at"),
    )


class EmailRuntimeConfig(Base):
    """Email runtime configuration (singleton)."""

    __tablename__ = "email_runtime_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requested_mode = Column(Text, nullable=False, server_default="disabled")  # EmailMode enum values
    email_freeze = Column(Boolean, nullable=False, server_default="false")
    reason = Column(Text, nullable=True)
    changed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=True)
    config_json = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    changed_by = relationship("User", foreign_keys=[changed_by_user_id])


class EmailSwitchEvent(Base):
    """Immutable audit trail for email mode switches."""

    __tablename__ = "email_switch_event"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    previous_config = Column(JSONB, nullable=False)
    new_config = Column(JSONB, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (Index("ix_email_switch_event_created_at", "created_at"),)
