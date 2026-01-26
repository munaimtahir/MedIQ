"""Freeze-updates enforcement: block state mutations when FREEZE_UPDATES is enabled."""

from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.core.app_exceptions import raise_app_error
from app.core.dependencies import get_db
from app.system.flags import is_freeze_updates


def require_mutations_allowed(module_key: str):
    """
    FastAPI dependency: block state-write requests when FREEZE_UPDATES is enabled.
    Use on learning mutation endpoints (mastery updates, queue writes, etc.).
    """

    def dependency(db: Session = Depends(get_db)) -> None:
        if is_freeze_updates(db):
            raise_app_error(
                status_code=status.HTTP_423_LOCKED,
                code="FREEZE_UPDATES_ACTIVE",
                message="Learning state mutations are disabled",
                details={"module": module_key},
            )

    return dependency
