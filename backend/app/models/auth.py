"""Authentication-related models (refresh tokens, password reset tokens, email verification tokens)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class RefreshToken(Base):
    """Refresh token model for token rotation and revocation."""

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String, unique=True, nullable=False, index=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by_token_id = Column(
        UUID(as_uuid=True), ForeignKey("refresh_tokens.id"), nullable=True
    )
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
    replaced_by_token = relationship(
        "RefreshToken", remote_side=[id], foreign_keys=[replaced_by_token_id]
    )

    def is_active(self) -> bool:
        """Check if token is active (not revoked and not expired)."""
        if self.revoked_at is not None:
            return False
        now = datetime.now(UTC)
        return now < self.expires_at


class PasswordResetToken(Base):
    """Password reset token model."""

    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")

    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        if self.used_at is not None:
            return False
        now = datetime.now(UTC)
        return now < self.expires_at


class EmailVerificationToken(Base):
    """Email verification token model."""

    __tablename__ = "email_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="email_verification_tokens")

    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        if self.used_at is not None:
            return False
        now = datetime.now(UTC)
        return now < self.expires_at

    def is_expired(self) -> bool:
        """Check if token is expired."""
        now = datetime.now(UTC)
        return now >= self.expires_at
