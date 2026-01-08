"""Admin system info endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import require_roles
from app.core.redis_client import is_redis_available
from app.db.session import get_db
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin/system", tags=["Admin - System"])


@router.get(
    "/info",
    summary="Get system information",
    description="Get system information for admin dashboard.",
)
async def get_system_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> dict:
    """Get system information."""
    # Check database connection
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        pass

    # Check Redis
    redis_connected = False
    if settings.REDIS_ENABLED:
        redis_connected = is_redis_available()

    return {
        "environment": settings.ENVIRONMENT if hasattr(settings, "ENVIRONMENT") else "development",
        "api_version": "v1",
        "backend_version": getattr(settings, "GIT_SHA", None) or "unknown",
        "db_connected": db_connected,
        "redis_connected": redis_connected if settings.REDIS_ENABLED else None,
    }
