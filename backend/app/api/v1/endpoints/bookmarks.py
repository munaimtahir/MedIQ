"""Bookmark endpoints for student users."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.bookmark import Bookmark
from app.models.question_cms import Question
from app.models.user import User
from app.schemas.bookmark import (
    BookmarkCreate,
    BookmarkOut,
    BookmarkUpdate,
    BookmarkWithQuestion,
)

router = APIRouter()


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/bookmarks", response_model=list[BookmarkWithQuestion])
async def list_bookmarks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
):
    """
    List all bookmarks for the current user with question details.

    Returns bookmarks ordered by most recent first.
    """
    # Get bookmarks with question details
    stmt = (
        select(Bookmark, Question)
        .join(Question, Bookmark.question_id == Question.id)
        .where(Bookmark.user_id == current_user.id)
        .order_by(Bookmark.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Transform to BookmarkWithQuestion
    bookmarks = []
    for bookmark, question in rows:
        bookmarks.append(
            BookmarkWithQuestion(
                id=bookmark.id,
                user_id=bookmark.user_id,
                question_id=bookmark.question_id,
                notes=bookmark.notes,
                created_at=bookmark.created_at,
                updated_at=bookmark.updated_at,
                question_stem=question.stem,
                question_status=question.status.value if question.status else "UNKNOWN",
                year_id=question.year_id,
                block_id=question.block_id,
                theme_id=question.theme_id,
                difficulty=question.difficulty,
                cognitive_level=question.cognitive_level,
            )
        )

    return bookmarks


@router.post("/bookmarks", response_model=BookmarkOut, status_code=201)
async def create_bookmark(
    bookmark_data: BookmarkCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Create a new bookmark for a question.

    If bookmark already exists, returns the existing bookmark.
    """
    # Check if bookmark already exists
    existing_stmt = select(Bookmark).where(
        Bookmark.user_id == current_user.id,
        Bookmark.question_id == bookmark_data.question_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Update notes if provided
        if bookmark_data.notes is not None:
            existing.notes = bookmark_data.notes
            await db.commit()
            await db.refresh(existing)
        return existing

    # Verify question exists
    question_stmt = select(Question).where(Question.id == bookmark_data.question_id)
    question_result = await db.execute(question_stmt)
    question = question_result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Create bookmark
    bookmark = Bookmark(
        user_id=current_user.id,
        question_id=bookmark_data.question_id,
        notes=bookmark_data.notes,
    )
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)

    return bookmark


@router.get("/bookmarks/{bookmark_id}", response_model=BookmarkOut)
async def get_bookmark(
    bookmark_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get a specific bookmark by ID."""
    stmt = select(Bookmark).where(Bookmark.id == bookmark_id)
    result = await db.execute(stmt)
    bookmark = result.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    if bookmark.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this bookmark")

    return bookmark


@router.patch("/bookmarks/{bookmark_id}", response_model=BookmarkOut)
async def update_bookmark(
    bookmark_id: UUID,
    bookmark_data: BookmarkUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Update a bookmark's notes."""
    stmt = select(Bookmark).where(Bookmark.id == bookmark_id)
    result = await db.execute(stmt)
    bookmark = result.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    if bookmark.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this bookmark")

    bookmark.notes = bookmark_data.notes
    await db.commit()
    await db.refresh(bookmark)

    return bookmark


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
async def delete_bookmark(
    bookmark_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Delete a bookmark."""
    stmt = select(Bookmark).where(Bookmark.id == bookmark_id)
    result = await db.execute(stmt)
    bookmark = result.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    if bookmark.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this bookmark")

    await db.delete(bookmark)
    await db.commit()

    return None


@router.get("/bookmarks/check/{question_id}", response_model=dict[str, bool | str | None])
async def check_bookmark(
    question_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Check if a question is bookmarked by the current user.

    Returns: {"is_bookmarked": bool, "bookmark_id": UUID | None}
    """
    stmt = select(Bookmark).where(
        Bookmark.user_id == current_user.id,
        Bookmark.question_id == question_id,
    )
    result = await db.execute(stmt)
    bookmark = result.scalar_one_or_none()

    return {
        "is_bookmarked": bookmark is not None,
        "bookmark_id": str(bookmark.id) if bookmark else None,
    }
