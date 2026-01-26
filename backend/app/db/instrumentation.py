"""SQLAlchemy instrumentation for slow SQL logging + per-request counters.

This module attaches SQLAlchemy event listeners to the Engine:
- Track per-request DB query count and total DB time (via contextvars).
- Log slow SQL queries with request_id correlation.

Design goals:
- **Always enabled** (dev/staging/prod) but only logs **slow queries** to avoid noise.
- Fail-open: instrumentation must never break application queries.
"""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.core.logging import get_logger
from app.middleware.request_context import (
    db_query_count_var,
    db_total_ms_var,
    db_top_slow_queries_var,
    get_request_id,
)

logger = get_logger(__name__)

SLOW_SQL_WARN_MS = 100
SLOW_SQL_ERROR_MS = 300
MAX_SQL_CHARS = 2000
TOP_N_SLOW = 5


def _normalize_sql(sql: str) -> str:
    # Collapse whitespace to make grouping easier in logs.
    return " ".join((sql or "").split())


def _severity_for_query_ms(query_ms: float) -> str | None:
    if query_ms > SLOW_SQL_ERROR_MS:
        return "error"
    if query_ms > SLOW_SQL_WARN_MS:
        return "warn"
    return None


def _track_slow_query(query_ms: float, sql: str, rowcount: int | None) -> None:
    """Maintain top-N slow queries for the request (in contextvars)."""

    try:
        current = list(db_top_slow_queries_var.get() or [])
        current.append(
            {
                "query_ms": float(query_ms),
                "sql": sql,
                "rowcount": rowcount,
            }
        )
        current.sort(key=lambda x: x.get("query_ms", 0.0), reverse=True)
        db_top_slow_queries_var.set(current[:TOP_N_SLOW])
    except Exception:
        # Best-effort only
        pass


def instrument_engine(engine: Engine) -> None:
    """Attach SQLAlchemy listeners to a sync Engine (idempotent)."""

    if getattr(engine, "_perf_instrumented", False):
        return
    setattr(engine, "_perf_instrumented", True)

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(
        conn, cursor, statement: str, parameters: Any, context, executemany: bool
    ) -> None:
        try:
            conn.info["_perf_query_start"] = time.perf_counter()
        except Exception:
            pass

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(
        conn, cursor, statement: str, parameters: Any, context, executemany: bool
    ) -> None:
        start = conn.info.get("_perf_query_start")
        if start is None:
            return

        try:
            query_ms = (time.perf_counter() - float(start)) * 1000.0
        except Exception:
            return

        # Update per-request counters (best-effort)
        try:
            db_query_count_var.set(int(db_query_count_var.get() or 0) + 1)
            db_total_ms_var.set(float(db_total_ms_var.get() or 0.0) + float(query_ms))
        except Exception:
            pass

        sev = _severity_for_query_ms(query_ms)
        if not sev:
            return

        # In prod, log slow SQL only (no verbose per-query logs).
        # In dev/staging, still only log slow SQL (keeps logs sane while catching regressions).
        try:
            sql_norm = _normalize_sql(statement)[:MAX_SQL_CHARS]
            rc = None
            try:
                rc = int(getattr(cursor, "rowcount", None))
            except Exception:
                rc = None

            _track_slow_query(query_ms=query_ms, sql=sql_norm, rowcount=rc)

            logger.warning(
                "slow_sql",
                extra={
                    "event": "slow_sql",
                    "severity": sev,
                    "request_id": get_request_id() or "unknown",
                    "query_ms": int(query_ms),
                    "rowcount": rc,
                    "sql": sql_norm,
                    "env": settings.ENV,
                },
            )
        except Exception:
            # Never break requests due to logging
            return

