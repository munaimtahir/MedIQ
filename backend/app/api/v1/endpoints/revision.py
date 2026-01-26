"""Revision Queue API endpoints."""

import logging
from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user, get_db
from app.models.learning_revision import RevisionQueue
from app.models.user import User
from app.schemas.revision import (
    BlockInfo,
    RevisionQueueItem,
    RevisionQueueListResponse,
    RevisionQueueUpdateRequest,
    ThemeInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# GET /v1/revision/queue
# ============================================================================


@router.get("/revision/queue", response_model=RevisionQueueListResponse)
async def get_revision_queue(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    scope: str = Query(default="today", pattern="^(today|week)$"),
    status: str = Query(default="DUE", pattern="^(DUE|DONE|SNOOZED|SKIPPED|ALL)$"),
):
    """
    Get revision queue items for the current user.

    Query Parameters:
    - scope: "today" (due_date == today) or "week" (due_date in next 7 days)
    - status: Filter by status (DUE, DONE, SNOOZED, SKIPPED, ALL)

    Returns list of revision items with theme/block info and reason.
    """
    # Determine date range
    today = date.today()

    if scope == "today":
        date_filter = RevisionQueue.due_date == today
    else:  # week
        week_end = today + timedelta(days=7)
        date_filter = and_(
            RevisionQueue.due_date >= today,
            RevisionQueue.due_date <= week_end,
        )

    # Build query
    stmt = (
        select(RevisionQueue)
        .where(
            and_(
                RevisionQueue.user_id == current_user.id,
                date_filter,
            )
        )
        .options(
            selectinload(RevisionQueue.theme),
            selectinload(RevisionQueue.block),
        )
        .order_by(RevisionQueue.priority_score.desc(), RevisionQueue.due_date.asc())
    )

    # Apply status filter
    if status != "ALL":
        stmt = stmt.where(RevisionQueue.status == status)

    result = await db.execute(stmt)
    queue_items = result.scalars().all()

    # Build response
    items = []
    for item in queue_items:
        items.append(
            RevisionQueueItem(
                id=item.id,
                due_date=item.due_date,
                status=item.status,
                priority_score=float(item.priority_score),
                recommended_count=item.recommended_count,
                block=BlockInfo(id=item.block.id, name=item.block.name),
                theme=ThemeInfo(id=item.theme.id, name=item.theme.name),
                reason=item.reason_json or {},
            )
        )

    return RevisionQueueListResponse(
        items=items,
        total=len(items),
    )


# ============================================================================
# PATCH /v1/revision/queue/{id}
# ============================================================================


@router.patch("/revision/queue/{item_id}", response_model=RevisionQueueItem)
async def update_revision_queue_item(
    item_id: UUID,
    request: RevisionQueueUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Update revision queue item status.

    Actions:
    - DONE: Mark as completed (only if due_date <= today)
    - SKIP: Mark as skipped
    - SNOOZE: Postpone by snooze_days (1-3 days)

    Enforces ownership (must be current user's item).
    """
    # Validate request
    try:
        request.validate_snooze()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Get item with ownership check
    stmt = (
        select(RevisionQueue)
        .where(RevisionQueue.id == item_id)
        .options(
            selectinload(RevisionQueue.theme),
            selectinload(RevisionQueue.block),
        )
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Revision item not found")

    if item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this item")

    # Apply action
    today = date.today()

    if request.action == "DONE":
        # Only allow marking as DONE if due_date <= today
        if item.due_date > today:
            raise HTTPException(status_code=422, detail="Cannot mark future items as DONE")
        item.status = "DONE"

    elif request.action == "SKIP":
        item.status = "SKIPPED"

    elif request.action == "SNOOZE":
        # Update due_date and status
        new_due_date = item.due_date + timedelta(days=request.snooze_days)
        item.due_date = new_due_date
        item.status = "SNOOZED"

        # Note: If a row with same (user_id, theme_id, new_due_date) exists,
        # the unique constraint will fail. For simplicity, we update the current row.
        # In production, you might want to handle this more gracefully.

    await db.commit()
    await db.refresh(item)

    # Return updated item
    return RevisionQueueItem(
        id=item.id,
        due_date=item.due_date,
        status=item.status,
        priority_score=float(item.priority_score),
        recommended_count=item.recommended_count,
        block=BlockInfo(id=item.block.id, name=item.block.name),
        theme=ThemeInfo(id=item.theme.id, name=item.theme.name),
        reason=item.reason_json or {},
    )
