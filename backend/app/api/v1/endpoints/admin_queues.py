"""Admin endpoints for queue statistics and job monitoring."""

import logging
from datetime import date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.jobs import JobRun
from app.models.queues import QueueStatsDaily, RevisionQueueTheme, RevisionQueueUserSummary
from app.models.syllabus import Block, Theme
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != "ADMIN":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admin access required")


class QueueStatsResponse(BaseModel):
    """Queue statistics response."""

    global_totals: dict[str, int]
    breakdown_by_theme: list[dict[str, Any]]
    breakdown_by_block: list[dict[str, Any]]
    last_regen_job: dict[str, Any] | None
    trend: list[dict[str, Any]]  # Last 7 days


@router.get("/admin/queues/stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get queue statistics (admin only).

    Returns:
    - global_totals: due_today, overdue, due_tomorrow
    - breakdown_by_theme: top 20 themes by due_today
    - breakdown_by_block: top blocks
    - last_regen_job: last job run status
    - trend: last 7 days snapshots
    """
    require_admin(current_user)

    # Get global totals
    stmt = select(
        func.sum(RevisionQueueUserSummary.due_today_total),
        func.sum(RevisionQueueUserSummary.overdue_total),
        func.sum(RevisionQueueUserSummary.due_tomorrow_total),
    )
    result = await db.execute(stmt)
    row = result.first()

    global_totals = {
        "due_today": int(row[0] or 0),
        "overdue": int(row[1] or 0),
        "due_tomorrow": int(row[2] or 0),
    }

    # Get breakdown by theme (top 20)
    stmt = (
        select(
            RevisionQueueTheme.theme_id,
            Theme.title,
            func.sum(RevisionQueueTheme.due_count_today).label("total_due"),
            func.sum(RevisionQueueTheme.overdue_count).label("total_overdue"),
        )
        .join(Theme, RevisionQueueTheme.theme_id == Theme.id)
        .group_by(RevisionQueueTheme.theme_id, Theme.title)
        .order_by(desc("total_due"))
        .limit(20)
    )
    result = await db.execute(stmt)
    theme_rows = result.all()

    breakdown_by_theme = [
        {
            "theme_id": row.theme_id,
            "theme_name": row.title,
            "due_today": int(row.total_due),
            "overdue": int(row.total_overdue),
        }
        for row in theme_rows
    ]

    # Get breakdown by block
    stmt = (
        select(
            Block.id,
            Block.title,
            func.sum(RevisionQueueTheme.due_count_today).label("total_due"),
            func.sum(RevisionQueueTheme.overdue_count).label("total_overdue"),
        )
        .join(Theme, RevisionQueueTheme.theme_id == Theme.id)
        .join(Block, Theme.block_id == Block.id)
        .group_by(Block.id, Block.title)
        .order_by(desc("total_due"))
    )
    result = await db.execute(stmt)
    block_rows = result.all()

    breakdown_by_block = [
        {
            "block_id": row.id,
            "block_name": row.title,
            "due_today": int(row.total_due),
            "overdue": int(row.total_overdue),
        }
        for row in block_rows
    ]

    # Get last regen job
    stmt = (
        select(JobRun)
        .where(JobRun.job_key == "revision_queue_regen")
        .order_by(desc(JobRun.created_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    last_job = result.scalar_one_or_none()

    last_regen_job = None
    if last_job:
        last_regen_job = {
            "id": str(last_job.id),
            "status": last_job.status,
            "started_at": last_job.started_at.isoformat() if last_job.started_at else None,
            "finished_at": last_job.finished_at.isoformat() if last_job.finished_at else None,
            "stats": last_job.stats_json,
            "error": last_job.error_text,
        }

    # Get trend (last 7 days)
    seven_days_ago = date.today() - timedelta(days=7)
    stmt = (
        select(QueueStatsDaily)
        .where(QueueStatsDaily.date >= seven_days_ago)
        .order_by(QueueStatsDaily.date)
    )
    result = await db.execute(stmt)
    daily_stats = result.scalars().all()

    trend = [
        {
            "date": stat.date.isoformat(),
            "due_today": stat.due_today_total,
            "overdue": stat.overdue_total,
            "due_tomorrow": stat.due_tomorrow_total,
            "users_with_due": stat.users_with_due,
        }
        for stat in daily_stats
    ]

    return QueueStatsResponse(
        global_totals=global_totals,
        breakdown_by_theme=breakdown_by_theme,
        breakdown_by_block=breakdown_by_block,
        last_regen_job=last_regen_job,
        trend=trend,
    )
