"""Health and readiness endpoints."""

from typing import Literal

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import get_request_id
from app.core.redis_client import is_redis_available
from app.db.session import get_db

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["ok"] = "ok"


class ReadinessCheck(BaseModel):
    """Individual readiness check result."""

    status: Literal["ok", "degraded", "down"]
    message: str | None = None


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    status: Literal["ok", "degraded", "down"]
    checks: dict[str, ReadinessCheck]
    request_id: str


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Simple health check endpoint. Returns 200 if the API is running.",
)
async def health_check() -> HealthResponse:
    """Health check endpoint - just checks if the process is alive."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Readiness check endpoint. Verifies database connectivity and other dependencies.",
)
async def readiness_check(
    request: Request,
    db: Session = Depends(get_db),
) -> ReadinessResponse:
    """Readiness check endpoint - checks dependencies."""
    request_id = get_request_id(request)
    checks: dict[str, ReadinessCheck] = {}
    overall_status: Literal["ok", "degraded", "down"] = "ok"

    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["db"] = ReadinessCheck(status="ok")
    except Exception as e:
        checks["db"] = ReadinessCheck(status="down", message=str(e))
        overall_status = "down"

    # Check Redis (optional)
    if settings.REDIS_ENABLED:
        if is_redis_available():
            checks["redis"] = ReadinessCheck(status="ok")
        else:
            checks["redis"] = ReadinessCheck(
                status="degraded", message="Redis unavailable"
            )
            # Only degrade if Redis is not required
            if not settings.REDIS_REQUIRED and overall_status == "ok":
                overall_status = "degraded"
            elif settings.REDIS_REQUIRED:
                overall_status = "down"
    else:
        checks["redis"] = ReadinessCheck(status="ok", message="Not enabled")

    return ReadinessResponse(
        status=overall_status,
        checks=checks,
        request_id=request_id,
    )

