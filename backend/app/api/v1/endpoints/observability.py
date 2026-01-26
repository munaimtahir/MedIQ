"""Observability and metrics endpoints (admin/internal)."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.jobs import JobRun
from app.models.performance import ApiPerfSample
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != "ADMIN":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admin access required")


class MetricsResponse(BaseModel):
    """Metrics response."""

    latency_p50: dict[str, float]  # route -> p50 latency
    latency_p95: dict[str, float]  # route -> p95 latency
    error_counts: dict[str, int]  # route -> error count
    job_status_summaries: dict[str, dict[str, Any]]  # job_key -> status summary


@router.get("/admin/observability/metrics", response_model=MetricsResponse)
async def get_metrics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get performance metrics (admin only).

    Returns:
    - latency_p50/p95 per route (from api_perf_sample, last 24h)
    - error counts per route
    - job status summaries
    """
    require_admin(current_user)

    # Get performance samples from last 24h
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(hours=24)

    stmt = (
        select(
            ApiPerfSample.route,
            func.percentile_cont(0.5).within_group(ApiPerfSample.duration_ms).label("p50"),
            func.percentile_cont(0.95).within_group(ApiPerfSample.duration_ms).label("p95"),
            func.count().label("total"),
        )
        .where(ApiPerfSample.occurred_at >= cutoff)
        .group_by(ApiPerfSample.route)
    )
    result = await db.execute(stmt)
    perf_rows = result.all()

    latency_p50 = {}
    latency_p95 = {}
    for row in perf_rows:
        latency_p50[row.route] = float(row.p50) if row.p50 else 0.0
        latency_p95[row.route] = float(row.p95) if row.p95 else 0.0

    # Get error counts
    stmt = (
        select(
            ApiPerfSample.route,
            func.count().label("error_count"),
        )
        .where(
            ApiPerfSample.occurred_at >= cutoff,
            ApiPerfSample.status_code >= 400,
        )
        .group_by(ApiPerfSample.route)
    )
    result = await db.execute(stmt)
    error_rows = result.all()

    error_counts = {row.route: int(row.error_count) for row in error_rows}

    # Get job status summaries
    stmt = (
        select(
            JobRun.job_key,
            JobRun.status,
            func.count().label("count"),
        )
        .group_by(JobRun.job_key, JobRun.status)
    )
    result = await db.execute(stmt)
    job_rows = result.all()

    job_status_summaries = {}
    for row in job_rows:
        if row.job_key not in job_status_summaries:
            job_status_summaries[row.job_key] = {}
        job_status_summaries[row.job_key][row.status] = int(row.count)

    return MetricsResponse(
        latency_p50=latency_p50,
        latency_p95=latency_p95,
        error_counts=error_counts,
        job_status_summaries=job_status_summaries,
    )
