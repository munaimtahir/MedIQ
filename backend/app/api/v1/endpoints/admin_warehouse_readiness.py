"""Admin warehouse readiness endpoint."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.warehouse.readiness import evaluate_warehouse_readiness

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


class ReadinessResponse(BaseModel):
    """Readiness response."""

    ready: bool
    checks: dict[str, dict[str, Any]]
    blocking_reasons: list[str]


@router.get("/admin/warehouse/readiness", response_model=ReadinessResponse)
async def get_warehouse_readiness(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get warehouse readiness status (admin only).

    Returns readiness evaluation with all checks and blocking reasons.
    """
    require_admin(current_user)

    readiness = evaluate_warehouse_readiness(db)

    return ReadinessResponse(
        ready=readiness.ready,
        checks={
            name: {
                "ok": check.ok,
                "details": check.details,
            }
            for name, check in readiness.checks.items()
        },
        blocking_reasons=readiness.blocking_reasons,
    )
