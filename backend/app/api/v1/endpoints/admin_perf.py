"""Admin performance endpoints (observability lite)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.performance import PerfRequestLog
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin/perf", tags=["Admin - Performance"])


def _parse_window(window: str) -> timedelta:
    w = (window or "24h").strip().lower()
    try:
        if w.endswith("h"):
            return timedelta(hours=int(w[:-1]))
        if w.endswith("d"):
            return timedelta(days=int(w[:-1]))
        if w.endswith("m"):
            return timedelta(minutes=int(w[:-1]))
    except Exception:
        pass
    raise HTTPException(status_code=400, detail="Invalid window. Use e.g. 15m, 1h, 24h, 7d.")


class TopRoute(BaseModel):
    path: str
    count: int
    p95_ms: float


class DbPressure(BaseModel):
    p95_db_ms: float
    avg_queries: float


class PerfSummaryResponse(BaseModel):
    window: str
    requests: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    slow_count: int
    top_routes: list[TopRoute]
    db: DbPressure


class PerfSlowRow(BaseModel):
    request_at: datetime
    method: str
    path: str
    status_code: int
    total_ms: int
    db_total_ms: int
    db_query_count: int
    user_role: str | None = None
    request_id: str | None = None
    sampled: bool


@router.get("/summary", response_model=PerfSummaryResponse)
def perf_summary(
    window: str = Query("24h", description="Window size (e.g. 15m, 1h, 24h, 7d)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    delta = _parse_window(window)
    cutoff = datetime.now(timezone.utc) - delta

    base = db.query(PerfRequestLog).filter(PerfRequestLog.request_at >= cutoff)

    requests = int(base.count())
    if requests == 0:
        return PerfSummaryResponse(
            window=window,
            requests=0,
            p50_ms=0.0,
            p95_ms=0.0,
            p99_ms=0.0,
            slow_count=0,
            top_routes=[],
            db=DbPressure(p95_db_ms=0.0, avg_queries=0.0),
        )

    # Percentiles
    pct = db.query(
        func.percentile_cont(0.5).within_group(PerfRequestLog.total_ms).label("p50"),
        func.percentile_cont(0.95).within_group(PerfRequestLog.total_ms).label("p95"),
        func.percentile_cont(0.99).within_group(PerfRequestLog.total_ms).label("p99"),
        func.percentile_cont(0.95).within_group(PerfRequestLog.db_total_ms).label("p95_db"),
        func.avg(PerfRequestLog.db_query_count).label("avg_q"),
    ).filter(PerfRequestLog.request_at >= cutoff)
    row = pct.first()

    slow_count = int(
        db.query(func.count())
        .select_from(PerfRequestLog)
        .filter(PerfRequestLog.request_at >= cutoff, PerfRequestLog.total_ms > 500)
        .scalar()
        or 0
    )

    # Top routes by p95
    top_stmt = (
        db.query(
            PerfRequestLog.path.label("path"),
            func.count().label("count"),
            func.percentile_cont(0.95).within_group(PerfRequestLog.total_ms).label("p95"),
        )
        .filter(PerfRequestLog.request_at >= cutoff)
        .group_by(PerfRequestLog.path)
        .order_by(func.percentile_cont(0.95).within_group(PerfRequestLog.total_ms).desc())
        .limit(10)
    )
    top_routes = [
        TopRoute(path=r.path, count=int(r.count), p95_ms=float(r.p95 or 0.0)) for r in top_stmt.all()
    ]

    return PerfSummaryResponse(
        window=window,
        requests=requests,
        p50_ms=float(row.p50 or 0.0),
        p95_ms=float(row.p95 or 0.0),
        p99_ms=float(row.p99 or 0.0),
        slow_count=slow_count,
        top_routes=top_routes,
        db=DbPressure(p95_db_ms=float(row.p95_db or 0.0), avg_queries=float(row.avg_q or 0.0)),
    )


@router.get("/slow", response_model=list[PerfSlowRow])
def perf_slow(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    rows = (
        db.query(PerfRequestLog)
        .filter(PerfRequestLog.total_ms > 500)
        .order_by(PerfRequestLog.request_at.desc())
        .limit(limit)
        .all()
    )
    return [
        PerfSlowRow(
            request_at=r.request_at,
            method=r.method,
            path=r.path,
            status_code=r.status_code,
            total_ms=r.total_ms,
            db_total_ms=r.db_total_ms,
            db_query_count=r.db_query_count,
            user_role=r.user_role,
            request_id=r.request_id,
            sampled=bool(r.sampled),
        )
        for r in rows
    ]


@router.post("/debug/slow-sql")
def debug_slow_sql(
    ms: int = Query(200, ge=1, le=2000, description="Sleep time in ms"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Dev-only helper to force a slow SQL query for observability checks."""

    if settings.ENV == "prod":
        raise HTTPException(status_code=404, detail="Not found")

    seconds = float(ms) / 1000.0
    db.execute(text("SELECT pg_sleep(:s)"), {"s": seconds})
    return {"status": "ok", "slept_ms": ms}

