"""Revision today endpoint - shows today's due themes."""

import logging
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.cache.helpers import revdash_key
from app.cache.redis import get_json, set_json
from app.core.dependencies import get_current_user, get_db
from app.models.queues import RevisionQueueTheme, RevisionQueueUserSummary
from app.models.syllabus import Block, Theme
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class ThemeDueInfo(BaseModel):
    """Theme due information."""

    theme_id: int  # Themes use Integer IDs
    theme_name: str
    block_id: int  # Blocks use Integer IDs
    block_name: str
    due_count_today: int
    overdue_count: int
    next_due_at: datetime | None


class RevisionTodayResponse(BaseModel):
    """Response for today's revision queue."""

    due_today_total: int
    overdue_total: int
    themes: list[ThemeDueInfo]
    recommended_theme_ids: list[int]  # Top N by due_count_today then weakness (Integer theme IDs)


@router.get("/learning/revision/today", response_model=RevisionTodayResponse)
def get_revision_today(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get today's due themes for the current user.

    Returns:
    - due_today_total: Total items due today
    - overdue_total: Total overdue items
    - themes: List of due themes with counts
    - recommended_theme_ids: Top N recommended themes (by due count, then weakness)
    """
    # Cache (60s) - user-specific dashboard aggregation, fail-open
    cache_key = revdash_key(str(current_user.id), date.today())
    cached = get_json(cache_key)
    if isinstance(cached, dict) and cached:
        return cached

    # Get user summary
    summary = (
        db.query(RevisionQueueUserSummary)
        .filter(RevisionQueueUserSummary.user_id == current_user.id)
        .first()
    )
    if not summary:
        out = RevisionTodayResponse(
            due_today_total=0,
            overdue_total=0,
            themes=[],
            recommended_theme_ids=[],
        )
        set_json(cache_key, jsonable_encoder(out), ttl_seconds=60)
        return out

    # Get theme-level details
    stmt = (
        select(
            RevisionQueueTheme.theme_id,
            RevisionQueueTheme.due_count_today,
            RevisionQueueTheme.overdue_count,
            RevisionQueueTheme.next_due_at,
            Theme.title,
            Theme.block_id,
            Block.title.label("block_title"),
        )
        .join(Theme, RevisionQueueTheme.theme_id == Theme.id)
        .join(Block, Theme.block_id == Block.id)
        .where(
            and_(
                RevisionQueueTheme.user_id == current_user.id,
                RevisionQueueTheme.due_count_today > 0,  # Only themes with due items
            )
        )
        .order_by(RevisionQueueTheme.due_count_today.desc(), RevisionQueueTheme.overdue_count.desc())
    )

    result = db.execute(stmt)
    rows = result.all()

    themes = []
    for row in rows:
        themes.append(
            ThemeDueInfo(
                theme_id=row.theme_id,
                theme_name=row.title,
                block_id=row.block_id,
                block_name=row.block_title,
                due_count_today=row.due_count_today,
                overdue_count=row.overdue_count,
                next_due_at=row.next_due_at,
            )
        )

    # Compute recommended themes (top N by due_count_today, then by weakness)
    # Get BKT mastery for tie-breaking
    recommended_theme_ids = []
    if themes:
        # Sort by due_count_today desc, then by mastery (lower = weaker = higher priority)
        from app.models.learning_mastery import UserThemeMastery

        theme_ids = [t.theme_id for t in themes]
        mastery_rows = (
            db.query(UserThemeMastery.theme_id, UserThemeMastery.mastery_score)
            .filter(UserThemeMastery.user_id == current_user.id, UserThemeMastery.theme_id.in_(theme_ids))
            .all()
        )
        mastery_by_theme = {int(tid): float(ms) for tid, ms in mastery_rows}

        theme_ids_with_mastery = [
            (t.theme_id, t.due_count_today, mastery_by_theme.get(int(t.theme_id), 0.5)) for t in themes
        ]

        # Sort: due_count desc, then mastery asc (weaker first)
        theme_ids_with_mastery.sort(key=lambda x: (-x[1], x[2]))
        recommended_theme_ids = [t[0] for t in theme_ids_with_mastery[:5]]  # Top 5

    out = RevisionTodayResponse(
        due_today_total=summary.due_today_total,
        overdue_total=summary.overdue_total,
        themes=themes,
        recommended_theme_ids=recommended_theme_ids,
    )
    set_json(cache_key, jsonable_encoder(out), ttl_seconds=60)
    return out


# Back-compat / budgeted student dashboard alias
@router.get("/student/revision", response_model=RevisionTodayResponse)
def get_student_revision_dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Student revision dashboard aggregation (alias for /learning/revision/today)."""

    return get_revision_today(db=db, current_user=current_user)
