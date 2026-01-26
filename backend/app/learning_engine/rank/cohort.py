"""Cohort key generation for rank prediction."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import AcademicYear, UserProfile
from app.models.user import User


async def cohort_key_for_user(db: AsyncSession, user_id: str) -> str:
    """
    Generate cohort key for a user.

    Priority:
    1. Use user's academic profile year
    2. Fallback to "year:0" (unknown)

    Args:
        db: Database session
        user_id: User ID (UUID string or UUID object)

    Returns:
        Cohort key string (e.g., "year:1", "year:2")
    """
    from uuid import UUID

    # Convert to UUID if string
    if isinstance(user_id, str):
        user_uuid = UUID(user_id)
    else:
        user_uuid = user_id

    # Get user's academic profile
    stmt = select(UserProfile).where(UserProfile.user_id == user_uuid)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if profile and profile.selected_year_id:
        year_stmt = select(AcademicYear).where(AcademicYear.id == profile.selected_year_id)
        year_result = await db.execute(year_stmt)
        year = year_result.scalar_one_or_none()

        if year:
            return f"year:{profile.selected_year_id}"

    # Fallback: unknown cohort
    return "year:0"


async def cohort_key_for_user_with_block(
    db: AsyncSession, user_id: str, block_id: int | None = None
) -> str:
    """
    Generate cohort key for a user with optional block.

    Args:
        db: Database session
        user_id: User ID
        block_id: Optional block ID

    Returns:
        Cohort key string (e.g., "year:1", "year:2:block:A")
    """
    base_key = await cohort_key_for_user(db, user_id)

    if block_id:
        # Get block code if available
        from app.models.syllabus import Block

        stmt = select(Block).where(Block.id == block_id)
        result = await db.execute(stmt)
        block = result.scalar_one_or_none()

        if block and block.code:
            return f"{base_key}:block:{block.code}"

    return base_key
