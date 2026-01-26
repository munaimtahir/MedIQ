"""Admin endpoints for tag quality debt."""

import logging
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.syllabus import Theme
from app.models.tag_quality import TagQualityDebtLog
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != "ADMIN":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admin access required")


class TagQualityDebtResponse(BaseModel):
    """Tag quality debt response."""

    total_debt_last_7d: int
    by_reason: dict[str, int]
    top_themes: list[dict[str, Any]]
    top_questions: list[dict[str, Any]]


@router.get("/admin/tag-quality", response_model=TagQualityDebtResponse)
async def get_tag_quality_debt(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get tag quality debt statistics (admin only).

    Returns:
    - total_debt_last_7d: Total debt count in last 7 days
    - by_reason: Breakdown by reason code
    - top_themes: Top themes with debt
    - top_questions: Top questions with debt
    """
    require_admin(current_user)

    # Get debt from last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    # Total count
    stmt = select(func.sum(TagQualityDebtLog.count)).where(
        TagQualityDebtLog.occurred_at >= seven_days_ago
    )
    result = await db.execute(stmt)
    total_debt = int(result.scalar() or 0)

    # By reason
    stmt = (
        select(TagQualityDebtLog.reason, func.sum(TagQualityDebtLog.count).label("total"))
        .where(TagQualityDebtLog.occurred_at >= seven_days_ago)
        .group_by(TagQualityDebtLog.reason)
    )
    result = await db.execute(stmt)
    by_reason = {row.reason: int(row.total) for row in result.all()}

    # Top themes
    stmt = (
        select(
            TagQualityDebtLog.theme_id,
            Theme.title,
            func.sum(TagQualityDebtLog.count).label("total"),
        )
        .join(Theme, TagQualityDebtLog.theme_id == Theme.id)
        .where(TagQualityDebtLog.occurred_at >= seven_days_ago)
        .group_by(TagQualityDebtLog.theme_id, Theme.title)
        .order_by(func.sum(TagQualityDebtLog.count).desc())
        .limit(20)
    )
    result = await db.execute(stmt)
    top_themes = [
        {"theme_id": row.theme_id, "theme_name": row.title, "count": int(row.total)}
        for row in result.all()
    ]

    # Top questions
    stmt = (
        select(
            TagQualityDebtLog.question_id,
            func.sum(TagQualityDebtLog.count).label("total"),
        )
        .where(TagQualityDebtLog.occurred_at >= seven_days_ago)
        .group_by(TagQualityDebtLog.question_id)
        .order_by(func.sum(TagQualityDebtLog.count).desc())
        .limit(20)
    )
    result = await db.execute(stmt)
    top_questions = [
        {"question_id": str(row.question_id), "count": int(row.total)} for row in result.all()
    ]

    return TagQualityDebtResponse(
        total_debt_last_7d=total_debt,
        by_reason=by_reason,
        top_themes=top_themes,
        top_questions=top_questions,
    )
