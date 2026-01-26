"""Admin freeze emergency switch functionality."""

from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.app_exceptions import raise_app_error
from app.core.dependencies import get_current_user, get_db
from app.models.admin_security import AdminSecurityRuntime
from app.models.user import User


def get_admin_freeze_config(db: Session) -> AdminSecurityRuntime:
    """Get or create admin security runtime config (singleton)."""
    config = db.query(AdminSecurityRuntime).filter(AdminSecurityRuntime.id == 1).first()
    if not config:
        config = AdminSecurityRuntime(
            id=1,
            admin_freeze=False,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def check_admin_freeze(db: Session) -> None:
    """
    Check if admin freeze is enabled and raise 423 if so.
    
    This should be called at the start of critical admin mutation endpoints.
    """
    config = get_admin_freeze_config(db)
    if config.admin_freeze:
        raise_app_error(
            status_code=status.HTTP_423_LOCKED,
            code="ADMIN_FREEZE",
            message="Admin mutations disabled",
            details={"reason": config.freeze_reason or "Admin freeze is active"},
        )


def require_admin_not_frozen():
    """
    FastAPI dependency to check admin freeze before allowing mutations.
    
    Usage:
        @router.post("/endpoint", dependencies=[Depends(require_admin_not_frozen())])
        async def endpoint(...):
            ...
    """

    def dependency(
        db: Session = Depends(get_db),
    ) -> None:
        """Check admin freeze status."""
        check_admin_freeze(db)

    return dependency
