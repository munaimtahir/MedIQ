"""Analytics endpoints for student performance metrics."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_async_db
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsOverview,
    BlockAnalytics,
    RecentSessionsResponse,
    ThemeAnalytics,
)
from app.services.analytics_service import (
    get_block_analytics,
    get_overview,
    get_recent_sessions,
    get_theme_analytics,
)

router = APIRouter()


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/analytics/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get student analytics overview.

    Returns overall performance metrics, block/theme breakdowns,
    trends, and weakest areas.
    """
    overview = await get_overview(db, current_user.id)
    return overview


@router.get("/analytics/block/{block_id}", response_model=BlockAnalytics)
async def get_block_analytics_endpoint(
    block_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get block-specific analytics.

    Returns performance metrics for a specific block,
    theme breakdowns, and trends.
    """
    analytics = await get_block_analytics(db, current_user.id, block_id)

    if analytics is None:
        raise HTTPException(status_code=404, detail="Block not found")

    return analytics


@router.get("/analytics/theme/{theme_id}", response_model=ThemeAnalytics)
async def get_theme_analytics_endpoint(
    theme_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get theme-specific analytics.

    Returns performance metrics for a specific theme and trends.
    """
    analytics = await get_theme_analytics(db, current_user.id, theme_id)

    if analytics is None:
        raise HTTPException(status_code=404, detail="Theme not found")

    return analytics


@router.get("/analytics/recent-sessions", response_model=RecentSessionsResponse)
async def get_recent_sessions_endpoint(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 10,
):
    """
    Get recent sessions for the current user.

    Returns both active and completed sessions, ordered by most recent.
    """
    sessions = await get_recent_sessions(db, current_user.id, limit=limit)
    return RecentSessionsResponse(sessions=sessions)
