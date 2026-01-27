"""Request timing middleware (ASGI; works on errors, too).

Guarantees that **every** HTTP response gets:
- X-Request-ID
- X-Response-Time-ms
- X-DB-Queries
- X-DB-Time-ms

Also emits a structured JSON log line and writes lightweight perf samples.
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from typing import Any

import structlog

from app.core.config import settings
from app.observability.logging import get_logger
from app.db.session import SessionLocal
from app.middleware.request_context import (
    db_query_count_var,
    db_total_ms_var,
    request_id_var,
)
from app.models.performance import PerfRequestLog

logger = get_logger(__name__)


def _severity_for_ms(total_ms: int) -> str | None:
    if total_ms > 1500:
        return "error"
    if total_ms > 500:
        return "warn"
    return None


class RequestTimingMiddleware:
    """ASGI middleware for timing + headers + sampling."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()

        # Ensure request_id exists (accept incoming header, else generate)
        headers = {k.lower(): v for (k, v) in (scope.get("headers") or [])}
        incoming = headers.get(b"x-request-id")
        request_id = incoming.decode("utf-8", errors="ignore") if incoming else str(uuid.uuid4())

        # Make it available via request.state.request_id and contextvars
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        token_request_id = request_id_var.set(request_id)
        token_db_q = db_query_count_var.set(0)
        token_db_ms = db_total_ms_var.set(0.0)

        # Bind request_id to structlog context for all logs in this request
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Log request lifecycle: request.start
        logger.info(
            "request.start",
            request_id=request_id,
            method=scope.get("method"),
            path=scope.get("path"),
            route=scope.get("route", {}).get("path") if scope.get("route") else None,
        )

        status_code: int | None = None

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code

            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 0) or 0)

                total_ms = int((time.perf_counter() - start) * 1000)
                db_queries = int(db_query_count_var.get() or 0)
                db_ms = int(float(db_total_ms_var.get() or 0.0))

                # Inject headers
                raw_headers = list(message.get("headers") or [])
                raw_headers.append((b"x-request-id", request_id.encode("utf-8")))
                raw_headers.append((b"x-response-time-ms", str(total_ms).encode("utf-8")))
                raw_headers.append((b"x-db-queries", str(db_queries).encode("utf-8")))
                raw_headers.append((b"x-db-time-ms", str(db_ms).encode("utf-8")))
                message["headers"] = raw_headers

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Structured log + sampling (best-effort)
            total_ms = int((time.perf_counter() - start) * 1000)
            db_queries = int(db_query_count_var.get() or 0)
            db_ms = int(float(db_total_ms_var.get() or 0.0))

            # Log sampling for high-volume endpoints (health, metrics, etc.)
            path = str(scope.get("path") or "")
            is_high_volume = path in ["/health", "/metrics", "/v1/health", "/"]
            sample_rate = 0.1 if is_high_volume else 1.0  # Sample 10% of high-volume endpoints

            user = None
            try:
                user = (scope.get("state") or {}).get("user")
            except Exception:
                user = None
            user_id = None
            user_role = None
            if user is not None:
                try:
                    user_id = str(getattr(user, "id", None) or "") or None
                    user_role = str(getattr(user, "role", None) or "") or None
                except Exception:
                    user_id = None
                    user_role = None

            # Log request lifecycle: request.end (with sampling for high-volume endpoints)
            if random.random() < sample_rate:
                log_data: dict[str, Any] = {
                    "event": "request.end",
                    "request_id": request_id,
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "route": scope.get("route", {}).get("path") if scope.get("route") else None,
                    "status_code": status_code,
                    "duration_ms": total_ms,
                    "db_query_count": db_queries,
                    "db_total_ms": db_ms,
                }
                if user_id:
                    log_data["user_id"] = user_id
                if user_role:
                    log_data["user_role"] = user_role
                sev = _severity_for_ms(total_ms)
                if sev:
                    log_data["severity"] = sev
                if is_high_volume:
                    log_data["sampled"] = True
                    log_data["sample_rate"] = sample_rate
                
                logger.info("request.end", **log_data)

            try:
                sample_rate = float(getattr(settings, "PERF_SAMPLE_RATE", 0.01))
            except Exception:
                sample_rate = 0.01

            is_slow = total_ms > 500
            sampled = random.random() < sample_rate
            if is_slow or sampled:
                asyncio.create_task(
                    _write_perf_request_log(
                        method=str(scope.get("method") or ""),
                        path=str(scope.get("path") or ""),
                        status_code=int(status_code or 0),
                        total_ms=int(total_ms),
                        db_total_ms=int(db_ms),
                        db_query_count=int(db_queries),
                        user_role=user_role,
                        request_id=request_id,
                        sampled=bool(sampled),
                    )
                )

            # Clear structlog context
            structlog.contextvars.clear_contextvars()
            
            request_id_var.reset(token_request_id)
            db_query_count_var.reset(token_db_q)
            db_total_ms_var.reset(token_db_ms)


async def _write_perf_request_log(
    *,
    method: str,
    path: str,
    status_code: int,
    total_ms: int,
    db_total_ms: int,
    db_query_count: int,
    user_role: str | None,
    request_id: str | None,
    sampled: bool,
) -> None:
    try:
        import anyio

        await anyio.to_thread.run_sync(
            _write_perf_request_log_sync,
            method,
            path,
            status_code,
            total_ms,
            db_total_ms,
            db_query_count,
            user_role,
            request_id,
            sampled,
        )
    except Exception:
        return


def _write_perf_request_log_sync(
    method: str,
    path: str,
    status_code: int,
    total_ms: int,
    db_total_ms: int,
    db_query_count: int,
    user_role: str | None,
    request_id: str | None,
    sampled: bool,
) -> None:
    try:
        db = SessionLocal()
        try:
            row = PerfRequestLog(
                method=method,
                path=path,
                status_code=status_code,
                total_ms=total_ms,
                db_total_ms=db_total_ms,
                db_query_count=db_query_count,
                user_role=user_role,
                request_id=request_id,
                sampled=sampled,
            )
            db.add(row)
            db.commit()
        finally:
            db.close()
    except Exception:
        return

