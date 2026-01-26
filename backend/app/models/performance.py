"""API performance sampling models."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class ApiPerfSample(Base):
    """API performance samples (sampled to manage volume)."""

    __tablename__ = "api_perf_sample"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    route = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    duration_ms = Column(Integer, nullable=False)
    user_role = Column(String(20), nullable=True)

    __table_args__ = (
        Index("ix_api_perf_sample_route_occurred", "route", "occurred_at"),
        Index("ix_api_perf_sample_occurred_at", "occurred_at"),
    )


class PerfRequestLog(Base):
    """Very light request sampling for admin performance dashboard."""

    __tablename__ = "perf_request_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    method = Column(String(10), nullable=False)
    path = Column(String(300), nullable=False)
    status_code = Column(Integer, nullable=False)

    total_ms = Column(Integer, nullable=False)
    db_total_ms = Column(Integer, nullable=False, server_default="0")
    db_query_count = Column(Integer, nullable=False, server_default="0")

    user_role = Column(String(20), nullable=True)
    request_id = Column(String(64), nullable=True)

    sampled = Column(Boolean, nullable=False, server_default="false")

    __table_args__ = (
        Index("ix_perf_request_log_request_at", "request_at"),
        Index("ix_perf_request_log_path_request_at", "path", "request_at"),
        Index("ix_perf_request_log_total_ms", "total_ms"),
    )
