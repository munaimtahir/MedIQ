"""CSP (Content Security Policy) violation report model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class CSPReport(Base):
    """CSP violation reports (sampled to manage volume)."""

    __tablename__ = "csp_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Report metadata
    document_uri = Column(Text, nullable=True)  # Page where violation occurred
    referrer = Column(Text, nullable=True)
    blocked_uri = Column(Text, nullable=True)  # Resource that was blocked
    violated_directive = Column(String(100), nullable=True)  # e.g., "script-src"
    effective_directive = Column(String(100), nullable=True)  # Actual directive that triggered
    original_policy = Column(Text, nullable=True)  # Full CSP policy
    source_file = Column(Text, nullable=True)  # Source file if available
    line_number = Column(String(20), nullable=True)  # Line number if available
    column_number = Column(String(20), nullable=True)  # Column number if available
    
    # Request metadata
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    
    # Sampling flag (for future use)
    sampled = Column(String(10), nullable=False, server_default="true")  # "true" or "false" as string

    __table_args__ = (
        Index("ix_csp_reports_created_at", "created_at"),
        Index("ix_csp_reports_violated_directive", "violated_directive"),
        Index("ix_csp_reports_blocked_uri", "blocked_uri", postgresql_ops={"blocked_uri": "varchar_pattern_ops"}),
    )
