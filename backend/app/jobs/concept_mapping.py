"""Helper functions for concept → theme mapping with fallback."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question_cms import Question

logger = logging.getLogger(__name__)


async def get_theme_id_for_concept(
    db: AsyncSession,
    concept_id: UUID,
) -> int | None:
    """
    Get theme_id (Integer) for a concept_id (UUID).

    For now, uses fallback: if concept_id maps to question, use question's theme_id.
    If no mapping exists, returns None (caller should use fallback).

    Args:
        db: Database session
        concept_id: Concept ID (UUID)

    Returns:
        Theme ID (Integer) or None if not found
    """
    # TODO: Implement proper concept → theme mapping when concept graph is ready
    # For now, try to find a question with this concept_id and use its theme_id
    # This is a placeholder implementation

    # Query questions by concept_id (if concept_id is stored as integer in questions)
    # For now, return None - will use fallback
    return None


async def get_theme_id_with_fallback(
    db: AsyncSession,
    concept_id: UUID,
    fallback_theme_id: int | None = None,
) -> int:
    """
    Get theme_id (Integer) for concept with fallback.

    If no mapping found, uses fallback_theme_id or creates pseudo-concept mapping.
    For BKT tag quality debt: if concept_id missing, use theme_id as pseudo-concept.

    Args:
        db: Database session
        concept_id: Concept ID (UUID)
        fallback_theme_id: Fallback theme ID (Integer) if mapping not found

    Returns:
        Theme ID (Integer, never None)
    """
    theme_id = await get_theme_id_for_concept(db, concept_id)

    if theme_id:
        return theme_id

    # Fallback: For now, use a hash of concept_id to map to a theme
    # In production, this would query a proper concept → theme mapping table
    if fallback_theme_id:
        return fallback_theme_id

    # Last resort: hash concept_id to get a pseudo-theme_id
    # This is a temporary solution until proper mapping exists
    logger.warning(f"No theme mapping found for concept {concept_id}, using hash fallback")
    # Use first 8 hex chars of UUID as integer (modulo to valid theme range)
    hash_val = int(str(concept_id).replace("-", "")[:8], 16)
    return (hash_val % 100) + 1  # Map to theme IDs 1-100 (placeholder)
