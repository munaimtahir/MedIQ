"""
Schemas for user allowed blocks - DEPRECATED.

These schemas are no longer used. The platform is now fully self-paced.
Kept for backward compatibility only.
"""

from typing import Optional

from pydantic import BaseModel, Field


class AllowedBlocksResponse(BaseModel):
    """Response schema for allowed blocks."""

    year_id: int
    allowed_block_ids: list[int] = Field(default_factory=list)
    max_allowed_order_no: Optional[int] = None  # Highest order_no among allowed blocks

    class Config:
        from_attributes = True


class AllowedBlocksUpdate(BaseModel):
    """Request schema for updating allowed blocks."""

    year_id: int
    allowed_block_ids: list[int] = Field(..., min_length=1)
