"""User model."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserRole(str, Enum):
    """User role enum."""

    STUDENT = "STUDENT"
    ADMIN = "ADMIN"
    REVIEWER = "REVIEWER"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=True)  # DB column; use .name for API compatibility
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)  # Nullable for OAuth-only users
    role = Column(String, nullable=False, default=UserRole.STUDENT.value)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    email_verification_sent_at = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @property
    def name(self) -> str:
        """API-friendly name; maps to full_name."""
        return self.full_name or ""

    @name.setter
    def name(self, value: str) -> None:
        self.full_name = value or None

    # Relationships
    auth_sessions = relationship(
        "AuthSession", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )
    email_verification_tokens = relationship(
        "EmailVerificationToken", back_populates="user", cascade="all, delete-orphan"
    )
    oauth_identities = relationship(
        "OAuthIdentity", back_populates="user", cascade="all, delete-orphan"
    )
    mfa_totp = relationship(
        "MFATOTP", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    mfa_backup_codes = relationship(
        "MFABackupCode", back_populates="user", cascade="all, delete-orphan"
    )
