"""Request body size limit middleware (input hardening).

Enforces max request body size at the app layer:
- Uses Content-Length when present; rejects immediately if over limit.
- When missing (chunked), stream-reads up to limit then aborts; never loads
  entire body into memory beyond limit.
Returns 413 Payload Too Large with structured error (PAYLOAD_TOO_LARGE).
Per-route override: /v1/admin/import/questions POST uses MAX_BODY_BYTES_IMPORT.
"""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings

# Methods that may have a body
_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


def _get_limit(scope: dict[str, Any]) -> int:
    path = (scope.get("path") or "").strip().rstrip("/")
    method = (scope.get("method") or "").upper()
    if method == "POST" and path.endswith("/v1/admin/import/questions"):
        return settings.MAX_BODY_BYTES_IMPORT
    return settings.MAX_BODY_BYTES_DEFAULT


def _content_length(scope: dict[str, Any]) -> int | None:
    for raw_name, raw_value in scope.get("headers") or []:
        if raw_name.lower() == b"content-length":
            try:
                return int(raw_value.decode("ascii").strip())
            except (ValueError, UnicodeDecodeError):
                return None
    return None


async def _send_413(scope: dict[str, Any], send: Send, limit: int) -> None:
    request_id = ""
    try:
        state = scope.get("state") or {}
        request_id = str(state.get("request_id", ""))
    except Exception:
        pass

    body = json.dumps(
        {
            "error": {
                "code": "PAYLOAD_TOO_LARGE",
                "message": "Request body exceeds maximum allowed size",
                "details": {"limit": limit},
                "request_id": request_id or None,
            }
        }
    ).encode("utf-8")

    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    if request_id:
        headers.append((b"x-request-id", request_id.encode("utf-8")))

    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": headers,
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})


class BodySizeLimitMiddleware:
    """ASGI middleware that enforces max request body size."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = (scope.get("method") or "").upper()
        if method not in _BODY_METHODS:
            await self.app(scope, receive, send)
            return

        limit = _get_limit(scope)
        cl = _content_length(scope)

        if cl is not None:
            if cl > limit:
                await _send_413(scope, send, limit)
                return
            await self.app(scope, receive, send)
            return

        # No Content-Length: chunked or unknown. Stream-read up to limit, then abort or forward.
        buffer: list[bytes] = []
        total = 0
        limit_exceeded = False

        async def consume() -> None:
            nonlocal total, limit_exceeded
            while True:
                m = await receive()
                if m["type"] == "http.disconnect":
                    break
                if m["type"] != "http.request":
                    continue
                body = m.get("body") or b""
                if body:
                    total += len(body)
                    if total > limit:
                        limit_exceeded = True
                        break
                    buffer.append(body)
                if not m.get("more_body", False):
                    break

        await consume()

        if limit_exceeded:
            await _send_413(scope, send, limit)
            return

        # Replay body via custom receive
        index: list[int] = [0]

        async def replay_receive() -> dict[str, Any]:
            if index[0] < len(buffer):
                chunk = buffer[index[0]]
                index[0] += 1
                more = index[0] < len(buffer)
                return {"type": "http.request", "body": chunk, "more_body": more}
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)
