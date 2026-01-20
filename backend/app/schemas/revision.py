"""Pydantic schemas for Revision Queue API."""

from datetime import date
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


# ============================================================================
# Revision Queue
# ============================================================================


class RevisionQueueItem(BaseModel):
    """Revision queue item with joined data."""

    id: UUID
    due_date: date
    status: str
    priority_score: float
    recommended_count: int
    block: BlockInfo
    theme: ThemeInfo
    reason: dict[str, Any]


class RevisionQueueListResponse(BaseModel):
    """List of revision queue items."""

    items: list[RevisionQueueItem]
    total: int


class RevisionQueueUpdateRequest(BaseModel):
    """Request to update revision queue item."""

    action: str = Field(..., pattern="^(DONE|SNOOZE|SKIP)$")
    snooze_days: int | None = Field(None, ge=1, le=3)

    def validate_snooze(self):
        """Validate that snooze_days is provided for SNOOZE action."""
        if self.action == "SNOOZE" and self.snooze_days is None:
            raise ValueError("snooze_days required for SNOOZE action")
        if self.action != "SNOOZE" and self.snooze_days is not None:
            raise ValueError("snooze_days only valid for SNOOZE action")
