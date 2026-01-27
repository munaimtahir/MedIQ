"""Test Package models for offline mobile caching."""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class PackageScope(str, PyEnum):
    """Package scope (program/module/block)."""

    PROGRAM = "PROGRAM"  # All questions for a program
    YEAR = "YEAR"  # All questions for a year
    BLOCK = "BLOCK"  # All questions for a block
    THEME = "THEME"  # All questions for a theme


class TestPackage(Base):
    """Test Package - immutable, versioned collection of questions for offline use."""

    __tablename__ = "test_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Package metadata
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    scope = Column(String(50), nullable=False)  # PROGRAM, YEAR, BLOCK, THEME
    
    # Scope identifiers (JSON for flexibility)
    scope_data = Column(JSONB, nullable=False)  # {year_id: 1, block_id: 2, theme_id: 3}
    
    # Versioning
    version = Column(Integer, nullable=False, default=1)
    version_hash = Column(String(64), nullable=False)  # SHA-256 hash of content
    
    # Content (immutable once published)
    questions_json = Column(JSONB, nullable=False)  # Array of question snapshots
    is_published = Column(Boolean, nullable=False, default=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint("scope", "scope_data", "version", name="uq_package_scope_version"),
        Index("ix_test_packages_scope", "scope"),
        Index("ix_test_packages_published", "is_published", "published_at"),
        Index("ix_test_packages_version_hash", "version_hash"),
    )
