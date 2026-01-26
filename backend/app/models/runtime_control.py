"""Runtime control framework models: profiles, overrides, audit, session snapshot."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class RuntimeProfile(Base):
    """Runtime profile (primary/fallback/shadow) with module default versions."""

    __tablename__ = "runtime_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(80), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="false")
    config = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, onupdate=func.now())


class ModuleOverride(Base):
    """Per-module version override (beats profile defaults)."""

    __tablename__ = "module_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_key = Column(String(80), unique=True, nullable=False)
    version_key = Column(String(40), nullable=False)
    is_enabled = Column(Boolean, nullable=False, server_default="true")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, onupdate=func.now())
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=True)

    updated_by_user = relationship("User", foreign_keys=[updated_by])


class SwitchAuditLog(Base):
    """Append-only audit log for flag/profile/override changes."""

    __tablename__ = "switch_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action_type = Column(String(80), nullable=False)
    before = Column(JSONB, nullable=True)
    after = Column(JSONB, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    actor = relationship("User", foreign_keys=[actor_user_id])


class SessionRuntimeSnapshot(Base):
    """Runtime snapshot at session creation (never changes mid-session)."""

    __tablename__ = "session_runtime_snapshot"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("test_sessions.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    profile_name = Column(String(80), nullable=False)
    resolved_modules = Column(JSONB, nullable=False, server_default="{}")
    flags = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("TestSession", back_populates="runtime_snapshot", uselist=False)


class TwoPersonApproval(Base):
    """Scaffold for optional two-person approval workflow."""

    __tablename__ = "two_person_approvals"

    request_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    requested_action = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, server_default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)

    requester = relationship("User", foreign_keys=[requested_by])
    approver = relationship("User", foreign_keys=[approved_by])
