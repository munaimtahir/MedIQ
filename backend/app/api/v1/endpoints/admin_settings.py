"""Admin settings endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.platform_settings import PlatformSettings
from app.models.user import User, UserRole
from app.schemas.platform_settings import (
    PlatformSettingsData,
    PlatformSettingsResponse,
    PlatformSettingsUpdate,
)

router = APIRouter(prefix="/admin/settings", tags=["Admin - Settings"])


def get_or_create_settings(db: Session) -> PlatformSettings:
    """Get or create platform settings singleton."""
    settings = db.query(PlatformSettings).filter(PlatformSettings.id == 1).first()
    if not settings:
        # Create default settings
        default_data = PlatformSettingsData().model_dump()
        settings = PlatformSettings(
            id=1,
            data=default_data,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get(
    "",
    response_model=PlatformSettingsResponse,
    summary="Get platform settings",
    description="Get current platform-wide settings.",
)
async def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> PlatformSettingsResponse:
    """Get platform settings."""
    settings = get_or_create_settings(db)

    # Validate and parse data
    try:
        settings_data = PlatformSettingsData.model_validate(settings.data)
    except Exception as e:
        # If data is invalid, reset to defaults
        default_data = PlatformSettingsData().model_dump()
        settings.data = default_data
        db.commit()
        settings_data = PlatformSettingsData.model_validate(default_data)
        # Suppress the original exception as we're handling it by resetting to defaults
        del e

    return PlatformSettingsResponse(
        data=settings_data,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
        updated_by_user_id=settings.updated_by_user_id,
    )


@router.put(
    "",
    response_model=PlatformSettingsResponse,
    summary="Update platform settings",
    description="Update platform-wide settings.",
)
async def update_settings(
    request: PlatformSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> PlatformSettingsResponse:
    """Update platform settings."""
    settings = get_or_create_settings(db)

    # Validate the data
    try:
        validated_data = PlatformSettingsData.model_validate(request.data.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid settings data: {str(e)}",
        ) from e

    # Update settings
    settings.data = validated_data.model_dump()
    settings.updated_at = datetime.now(UTC)
    settings.updated_by_user_id = current_user.id

    try:
        db.commit()
        db.refresh(settings)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}",
        ) from e

    return PlatformSettingsResponse(
        data=validated_data,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
        updated_by_user_id=settings.updated_by_user_id,
    )
