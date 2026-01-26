"""Exam mode gating dependency for blocking heavy operations."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.app_exceptions import raise_app_error
from app.db.session import get_db
from app.system.flags import is_exam_mode


def require_not_exam_mode(action_name: str):
    """
    FastAPI dependency to block heavy operations when exam mode is enabled.
    
    Usage:
        @router.post("/endpoint", dependencies=[Depends(require_not_exam_mode("analytics_recompute"))])
        async def endpoint(...):
            ...
    
    Args:
        action_name: Name of the action being blocked (for error message)
    
    Returns:
        Dependency function that raises 423 if exam mode is enabled
    """
    def dependency(
        db: Session = Depends(get_db),
    ) -> None:
        """Check exam mode and block if enabled."""
        if is_exam_mode(db):
            raise_app_error(
                status_code=status.HTTP_423_LOCKED,
                code="EXAM_MODE_ACTIVE",
                message="Action blocked during exam mode",
                details={"action": action_name},
            )
    
    return dependency
