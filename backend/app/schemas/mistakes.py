"""Pydantic schemas for Mistakes API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Nested Models
# ============================================================================


class BlockInfo(BaseModel):
    """Block information."""

    id: UUID
    name: str


class ThemeInfo(BaseModel):
    """Theme information."""

    id: UUID
    name: str


class QuestionInfo(BaseModel):
    """Question information."""

    id: UUID
    stem_preview: str


class ThemeCount(BaseModel):
    """Theme with count."""

    theme: ThemeInfo
    wrong: int


class BlockCount(BaseModel):
    """Block with count."""

    block: BlockInfo
    wrong: int


# ============================================================================
# Mistakes Summary
# ============================================================================


class MistakesSummaryResponse(BaseModel):
    """Summary of mistakes."""

    range_days: int
    total_wrong: int
    counts_by_type: dict[str, int]
    top_themes: list[ThemeCount]
    top_blocks: list[BlockCount]


# ============================================================================
# Mistakes List
# ============================================================================


class MistakeItem(BaseModel):
    """Single mistake item."""

    created_at: datetime
    mistake_type: str
    severity: int
    theme: ThemeInfo
    block: BlockInfo
    question: QuestionInfo
    evidence: dict[str, Any]


class MistakesListResponse(BaseModel):
    """Paginated list of mistakes."""

    page: int
    page_size: int
    total: int
    items: list[MistakeItem]
