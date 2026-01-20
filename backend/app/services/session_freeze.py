"""Service for freezing question content in sessions."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question_cms import Question, QuestionVersion


async def freeze_question(db: AsyncSession, question_id: UUID) -> tuple[UUID | None, dict[str, Any] | None]:
    """
    Freeze question content for a session.

    Strategy:
    1. Try to get the latest version_id from question_versions
    2. If available, return (version_id, None) - preferred
    3. Otherwise, create snapshot_json from current question - fallback

    Args:
        db: Database session
        question_id: Question ID to freeze

    Returns:
        Tuple of (question_version_id, snapshot_json)
        - If version system works: (version_id, None)
        - If fallback needed: (None, snapshot_dict)
    """
    # Try to get latest version
    version_stmt = (
        select(QuestionVersion)
        .where(QuestionVersion.question_id == question_id)
        .order_by(QuestionVersion.version_number.desc())
        .limit(1)
    )
    version_result = await db.execute(version_stmt)
    latest_version = version_result.scalar_one_or_none()

    if latest_version:
        # Preferred: use version_id
        return (latest_version.id, None)

    # Fallback: create snapshot from current question
    question_stmt = select(Question).where(Question.id == question_id)
    question_result = await db.execute(question_stmt)
    question = question_result.scalar_one_or_none()

    if not question:
        raise ValueError(f"Question {question_id} not found")

    # Build snapshot JSON
    snapshot = {
        "stem": question.stem,
        "option_a": question.option_a,
        "option_b": question.option_b,
        "option_c": question.option_c,
        "option_d": question.option_d,
        "option_e": question.option_e,
        "correct_index": question.correct_index,
        "explanation_md": question.explanation_md,
        # Metadata
        "year_id": question.year_id,
        "block_id": question.block_id,
        "theme_id": question.theme_id,
        "source_book": question.source_book,
        "source_page": question.source_page,
    }

    return (None, snapshot)


async def get_frozen_content(
    db: AsyncSession,
    question_id: UUID,
    version_id: UUID | None,
    snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Retrieve frozen question content.

    Args:
        db: Database session
        question_id: Question ID
        version_id: Question version ID (if available)
        snapshot: Snapshot JSON (if version not available)

    Returns:
        Dictionary with question content
    """
    if version_id:
        # Load from version
        version_stmt = select(QuestionVersion).where(QuestionVersion.id == version_id)
        version_result = await db.execute(version_stmt)
        version = version_result.scalar_one_or_none()

        if not version:
            raise ValueError(f"QuestionVersion {version_id} not found")

        return {
            "question_id": question_id,
            "stem": version.stem,
            "option_a": version.option_a,
            "option_b": version.option_b,
            "option_c": version.option_c,
            "option_d": version.option_d,
            "option_e": version.option_e,
            "correct_index": version.correct_index,
            "explanation_md": version.explanation_md,
            "year_id": version.year_id,
            "block_id": version.block_id,
            "theme_id": version.theme_id,
            "source_book": version.source_book,
            "source_page": version.source_page,
        }
    elif snapshot:
        # Use snapshot
        return {
            "question_id": question_id,
            **snapshot,
        }
    else:
        raise ValueError("Neither version_id nor snapshot available for frozen content")
