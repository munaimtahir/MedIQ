"""OAuth identity models."""

import uuid
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class OAuthProvider(str, Enum):
    """OAuth provider enum."""

    GOOGLE = "GOOGLE"
    MICROSOFT = "MICROSOFT"


class OAuthIdentity(Base):
    """OAuth identity model for linking external providers to users."""

    __tablename__ = "oauth_identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False)
    provider_subject = Column(String, nullable=False)  # OIDC 'sub' claim
    email_at_link_time = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="oauth_identities")

    # Unique constraint: one identity per provider+subject
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_oauth_provider_subject"),
    )

