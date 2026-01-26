"""User learning preferences endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user_prefs import UserLearningPrefs
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class LearningPrefsUpdate(BaseModel):
    """Request to update learning preferences."""

    revision_daily_target: int | None = None
    spacing_multiplier: float | None = None  # 0.8 = more frequent, 1.2 = less frequent
    retention_target_override: float | None = None  # Optional override for desired_retention


class LearningPrefsResponse(BaseModel):
    """Learning preferences response."""

    revision_daily_target: int | None
    spacing_multiplier: float
    retention_target_override: float | None

    class Config:
        """Pydantic config."""

        from_attributes = True


@router.get("/users/me/preferences/learning", response_model=LearningPrefsResponse)
async def get_learning_prefs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current user's learning preferences."""
    prefs = await db.get(UserLearningPrefs, current_user.id)

    if not prefs:
        # Return defaults
        return LearningPrefsResponse(
            revision_daily_target=None,
            spacing_multiplier=1.0,
            retention_target_override=None,
        )

    return LearningPrefsResponse(
        revision_daily_target=prefs.revision_daily_target,
        spacing_multiplier=float(prefs.spacing_multiplier),
        retention_target_override=float(prefs.retention_target_override) if prefs.retention_target_override else None,
    )


@router.patch("/users/me/preferences/learning", response_model=LearningPrefsResponse)
async def update_learning_prefs(
    request: LearningPrefsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Update current user's learning preferences."""
    from sqlalchemy.dialects.postgresql import insert
    from datetime import datetime

    # Validate spacing_multiplier
    if request.spacing_multiplier is not None:
        if not (0.5 <= request.spacing_multiplier <= 2.0):
            raise HTTPException(
                status_code=400, detail="spacing_multiplier must be between 0.5 and 2.0"
            )

    # Validate retention_target_override
    if request.retention_target_override is not None:
        if not (0.7 <= request.retention_target_override <= 0.95):
            raise HTTPException(
                status_code=400, detail="retention_target_override must be between 0.7 and 0.95"
            )

    # Upsert preferences
    stmt = insert(UserLearningPrefs).values(
        {
            "user_id": current_user.id,
            "revision_daily_target": request.revision_daily_target,
            "spacing_multiplier": request.spacing_multiplier or 1.0,
            "retention_target_override": request.retention_target_override,
            "updated_at": datetime.utcnow(),
        }
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id"],
        set_={
            "revision_daily_target": stmt.excluded.revision_daily_target,
            "spacing_multiplier": stmt.excluded.spacing_multiplier,
            "retention_target_override": stmt.excluded.retention_target_override,
            "updated_at": stmt.excluded.updated_at,
        },
    )

    await db.execute(stmt)
    await db.commit()

    # Return updated prefs
    prefs = await db.get(UserLearningPrefs, current_user.id)
    if not prefs:
        return LearningPrefsResponse(
            revision_daily_target=request.revision_daily_target,
            spacing_multiplier=request.spacing_multiplier or 1.0,
            retention_target_override=request.retention_target_override,
        )

    return LearningPrefsResponse.model_validate(prefs)
