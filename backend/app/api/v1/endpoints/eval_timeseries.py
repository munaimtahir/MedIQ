"""Evaluation metrics timeseries endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.eval import EvalMetric, EvalRun
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != "ADMIN":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admin access required")


class MetricTimeseriesPoint(BaseModel):
    """Single point in metrics timeseries."""

    date: str
    value: float
    run_id: str
    suite_name: str
    suite_versions: dict[str, str]


class MetricTimeseriesResponse(BaseModel):
    """Metrics timeseries response."""

    metric: str
    window: str
    points: list[MetricTimeseriesPoint]


@router.get("/admin/evaluation/metrics/timeseries", response_model=MetricTimeseriesResponse)
async def get_metric_timeseries(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    metric: str = Query(..., description="Metric name (logloss, brier, ece)"),
    window: str = Query(default="30d", description="Time window (e.g., 30d, 7d)"),
):
    """
    Get metrics timeseries for shadow evaluation dashboard (admin only).

    Returns time-series data for a specific metric over the specified window.
    """
    require_admin(current_user)

    # Parse window
    if window.endswith("d"):
        days = int(window[:-1])
    else:
        days = 30  # Default

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get runs with this metric
    stmt = (
        select(
            EvalRun.id,
            EvalRun.suite_name,
            EvalRun.suite_versions,
            EvalRun.finished_at,
            EvalRun.created_at,
            EvalMetric.value,
        )
        .join(EvalMetric, EvalRun.id == EvalMetric.run_id)
        .where(
            and_(
                EvalMetric.metric_name == metric,
                EvalMetric.scope_type == "GLOBAL",
                EvalRun.status == "SUCCEEDED",
                EvalRun.finished_at >= cutoff if EvalRun.finished_at else EvalRun.created_at >= cutoff,
            )
        )
        .order_by(EvalRun.finished_at.desc() if EvalRun.finished_at else EvalRun.created_at.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    points = []
    for row in rows:
        date_val = row.finished_at or row.created_at
        points.append(
            MetricTimeseriesPoint(
                date=date_val.date().isoformat(),
                value=float(row.value),
                run_id=str(row.id),
                suite_name=row.suite_name,
                suite_versions=row.suite_versions or {},
            )
        )

    return MetricTimeseriesResponse(
        metric=metric,
        window=window,
        points=points,
    )
