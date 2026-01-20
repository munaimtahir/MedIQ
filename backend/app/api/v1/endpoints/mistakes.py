"""Mistakes API endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.mistakes import MistakeLog
from app.models.question_cms import Question
from app.models.syllabus import Block, Theme
from app.models.user import User
from app.schemas.mistakes import (
    BlockCount,
    BlockInfo,
    MistakeItem,
    MistakesListResponse,
    MistakesSummaryResponse,
    QuestionInfo,
    ThemeCount,
    ThemeInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# GET /v1/mistakes/summary
# ============================================================================


@router.get("/mistakes/summary", response_model=MistakesSummaryResponse)
async def get_mistakes_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    range_days: int = Query(default=30, ge=1, le=365),
):
    """
    Get summary of mistakes for the current user.
    
    Query Parameters:
    - range_days: Number of days to look back (default: 30)
    
    Returns:
    - Total wrong count
    - Counts by mistake type
    - Top themes with most mistakes
    - Top blocks with most mistakes
    """
    # Calculate cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=range_days)
    
    # Get total wrong and counts by type
    stmt = (
        select(
            func.count(MistakeLog.id).label("total"),
            MistakeLog.mistake_type,
        )
        .where(
            and_(
                MistakeLog.user_id == current_user.id,
                MistakeLog.created_at >= cutoff_date,
            )
        )
        .group_by(MistakeLog.mistake_type)
    )
    result = await db.execute(stmt)
    type_counts = result.all()
    
    total_wrong = sum(row.total for row in type_counts)
    counts_by_type = {row.mistake_type: row.total for row in type_counts}
    
    # Get top themes
    theme_stmt = (
        select(
            MistakeLog.theme_id,
            Theme.name,
            func.count(MistakeLog.id).label("wrong_count"),
        )
        .join(Theme, MistakeLog.theme_id == Theme.id)
        .where(
            and_(
                MistakeLog.user_id == current_user.id,
                MistakeLog.created_at >= cutoff_date,
                MistakeLog.theme_id.isnot(None),
            )
        )
        .group_by(MistakeLog.theme_id, Theme.name)
        .order_by(func.count(MistakeLog.id).desc())
        .limit(5)
    )
    theme_result = await db.execute(theme_stmt)
    theme_rows = theme_result.all()
    
    top_themes = [
        ThemeCount(
            theme=ThemeInfo(id=row.theme_id, name=row.name),
            wrong=row.wrong_count,
        )
        for row in theme_rows
    ]
    
    # Get top blocks
    block_stmt = (
        select(
            MistakeLog.block_id,
            Block.name,
            func.count(MistakeLog.id).label("wrong_count"),
        )
        .join(Block, MistakeLog.block_id == Block.id)
        .where(
            and_(
                MistakeLog.user_id == current_user.id,
                MistakeLog.created_at >= cutoff_date,
                MistakeLog.block_id.isnot(None),
            )
        )
        .group_by(MistakeLog.block_id, Block.name)
        .order_by(func.count(MistakeLog.id).desc())
        .limit(5)
    )
    block_result = await db.execute(block_stmt)
    block_rows = block_result.all()
    
    top_blocks = [
        BlockCount(
            block=BlockInfo(id=row.block_id, name=row.name),
            wrong=row.wrong_count,
        )
        for row in block_rows
    ]
    
    return MistakesSummaryResponse(
        range_days=range_days,
        total_wrong=total_wrong,
        counts_by_type=counts_by_type,
        top_themes=top_themes,
        top_blocks=top_blocks,
    )


# ============================================================================
# GET /v1/mistakes/list
# ============================================================================


@router.get("/mistakes/list", response_model=MistakesListResponse)
async def get_mistakes_list(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    range_days: int = Query(default=30, ge=1, le=365),
    block_id: UUID | None = Query(default=None),
    theme_id: UUID | None = Query(default=None),
    mistake_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
):
    """
    Get paginated list of mistakes for the current user.
    
    Query Parameters:
    - range_days: Number of days to look back (default: 30)
    - block_id: Filter by block (optional)
    - theme_id: Filter by theme (optional)
    - mistake_type: Filter by mistake type (optional)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 50)
    
    Returns paginated list with question preview and evidence.
    """
    # Calculate cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=range_days)
    
    # Build base query
    filters = [
        MistakeLog.user_id == current_user.id,
        MistakeLog.created_at >= cutoff_date,
    ]
    
    if block_id:
        filters.append(MistakeLog.block_id == block_id)
    
    if theme_id:
        filters.append(MistakeLog.theme_id == theme_id)
    
    if mistake_type:
        filters.append(MistakeLog.mistake_type == mistake_type)
    
    # Get total count
    count_stmt = select(func.count(MistakeLog.id)).where(and_(*filters))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()
    
    # Get paginated items
    offset = (page - 1) * page_size
    
    stmt = (
        select(MistakeLog)
        .where(and_(*filters))
        .options(
            selectinload(MistakeLog.theme),
            selectinload(MistakeLog.block),
            selectinload(MistakeLog.question),
        )
        .order_by(MistakeLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    
    result = await db.execute(stmt)
    mistakes = result.scalars().all()
    
    # Build response items
    items = []
    for mistake in mistakes:
        # Get stem preview (truncate to 140 chars)
        stem_preview = ""
        if mistake.question:
            stem_preview = mistake.question.stem_text[:140]
            if len(mistake.question.stem_text) > 140:
                stem_preview += "..."
        
        items.append(
            MistakeItem(
                created_at=mistake.created_at,
                mistake_type=mistake.mistake_type,
                severity=mistake.severity,
                theme=ThemeInfo(
                    id=mistake.theme.id,
                    name=mistake.theme.name,
                ) if mistake.theme else ThemeInfo(id=UUID(int=0), name="Unknown"),
                block=BlockInfo(
                    id=mistake.block.id,
                    name=mistake.block.name,
                ) if mistake.block else BlockInfo(id=UUID(int=0), name="Unknown"),
                question=QuestionInfo(
                    id=mistake.question_id,
                    stem_preview=stem_preview,
                ),
                evidence=mistake.evidence_json or {},
            )
        )
    
    return MistakesListResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=items,
    )
