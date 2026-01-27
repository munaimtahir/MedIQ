"""Analytics endpoints for student performance metrics."""

import base64
import json
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import CursorPaginationParams, cursor_pagination_params
from app.core.dependencies import get_current_user
from app.db.session import get_async_db
from app.models.session import TestSession
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsOverview,
    BlockAnalytics,
    RecentSessionSummary,
    RecentSessionsCursorResponse,
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


@router.get("/overview", response_model=AnalyticsOverview)
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


@router.get("/block/{block_id}", response_model=BlockAnalytics)
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


@router.get("/theme/{theme_id}", response_model=ThemeAnalytics)
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


@router.get("/recent-sessions", response_model=RecentSessionsResponse)
async def get_recent_sessions_endpoint(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 10,
):
    """
    Get recent sessions for the current user (legacy, page-based).

    Returns both active and completed sessions, ordered by most recent.
    """
    sessions = await get_recent_sessions(db, current_user.id, limit=limit)
    return RecentSessionsResponse(sessions=sessions)


# ============================================================================
# GET /v1/analytics/recent-sessions:cursor (cursor-based pagination for mobile)
# ============================================================================


def _encode_session_cursor(session_id: UUID, started_at: datetime) -> str:
    """Encode cursor from session ID and timestamp."""
    cursor_data = {
        "id": str(session_id),
        "started_at": started_at.isoformat(),
    }
    cursor_json = json.dumps(cursor_data, sort_keys=True)
    return base64.b64encode(cursor_json.encode()).decode()


def _decode_session_cursor(cursor: str) -> tuple[UUID, datetime]:
    """Decode cursor to session ID and timestamp."""
    try:
        cursor_json = base64.b64decode(cursor.encode()).decode()
        cursor_data = json.loads(cursor_json)
        return UUID(cursor_data["id"]), datetime.fromisoformat(cursor_data["started_at"])
    except (ValueError, KeyError, json.JSONDecodeError):
        raise ValueError("Invalid cursor format")


@router.get("/recent-sessions:cursor", response_model=RecentSessionsCursorResponse)
async def get_recent_sessions_cursor(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    pagination: Annotated[CursorPaginationParams, Depends(cursor_pagination_params)],
):
    """
    Get recent sessions with cursor pagination (mobile-safe).

    Returns both active and completed sessions, ordered by most recent.
    """
    # Build base query
    filters = [TestSession.user_id == current_user.id]

    # Apply cursor if provided
    if pagination.cursor:
        try:
            cursor_id, cursor_started_at = _decode_session_cursor(pagination.cursor)
            # Get items after cursor (started_at < cursor OR (started_at = cursor AND id < cursor_id))
            filters.append(
                (TestSession.started_at < cursor_started_at)
                | (
                    (TestSession.started_at == cursor_started_at)
                    & (TestSession.id < cursor_id)
                )
            )
        except ValueError:
            # Invalid cursor - return empty result
            return RecentSessionsCursorResponse(items=[], next_cursor=None, has_more=False)

    # Get sessions (limit + 1 to check if there are more)
    stmt = (
        select(TestSession)
        .where(*filters)
        .order_by(TestSession.started_at.desc(), TestSession.id.desc())
        .limit(pagination.limit + 1)
    )

    result = await db.execute(stmt)
    sessions = result.scalars().all()

    # Check if there are more items
    has_more = len(sessions) > pagination.limit
    if has_more:
        sessions = sessions[:-1]  # Remove the extra item

    # Transform to RecentSessionSummary
    items = []
    for session in sessions:
        # Calculate score if completed
        score_correct = None
        score_total = None
        score_pct = None
        if session.status.value in ["SUBMITTED", "EXPIRED"]:
            # Get answers for this session
            from app.models.session import SessionAnswer
            answers_stmt = select(SessionAnswer).where(SessionAnswer.session_id == session.id)
            answers_result = await db.execute(answers_stmt)
            answers = answers_result.scalars().all()
            score_total = len(answers)
            score_correct = sum(1 for a in answers if a.is_correct is True)
            score_pct = round((score_correct / score_total * 100), 2) if score_total > 0 else 0.0

        items.append(
            RecentSessionSummary(
                session_id=session.id,
                title=session.title or f"Session {session.id}",
                status=session.status.value,
                score_correct=score_correct,
                score_total=score_total,
                score_pct=score_pct,
                block_id=session.block_id,
                theme_id=session.theme_id,
                started_at=session.started_at,
                submitted_at=session.submitted_at,
            )
        )

    # Generate next cursor from last item
    next_cursor = None
    if has_more and sessions:
        last_session = sessions[-1]
        next_cursor = _encode_session_cursor(last_session.id, last_session.started_at)

    return RecentSessionsCursorResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    )
