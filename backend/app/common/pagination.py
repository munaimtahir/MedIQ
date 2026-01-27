"""Pagination helpers (guardrails for admin performance).

Supports both page-based (legacy) and cursor-based (mobile-safe) pagination.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
DEFAULT_CURSOR_LIMIT = 50
MAX_CURSOR_LIMIT = 100


class PaginationParams(BaseModel):
    """Page-based pagination (legacy, for web/admin)."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class CursorPaginationParams(BaseModel):
    """Cursor-based pagination (mobile-safe)."""

    cursor: str | None = Field(default=None, description="Cursor token for pagination")
    limit: int = Field(default=DEFAULT_CURSOR_LIMIT, ge=1, le=MAX_CURSOR_LIMIT)


class PaginatedResponse(BaseModel, Generic[T]):
    """Page-based pagination response (legacy)."""

    items: list[T]
    page: int
    page_size: int
    total: int


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based pagination response (mobile-safe).
    
    Format: {items, next_cursor, has_more}
    Compatible with mobile clients requiring efficient pagination.
    """

    items: list[T]
    next_cursor: str | None = Field(default=None, description="Cursor for next page, null if no more")
    has_more: bool = Field(description="True if more items available")


def pagination_params(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, description="Page size (max 100)"),
) -> PaginationParams:
    """Dependency for page-based pagination."""
    if page_size > MAX_PAGE_SIZE:
        raise HTTPException(status_code=400, detail=f"page_size must be <= {MAX_PAGE_SIZE}")
    return PaginationParams(page=page, page_size=page_size)


def cursor_pagination_params(
    cursor: str | None = Query(None, description="Cursor token for pagination"),
    limit: int = Query(DEFAULT_CURSOR_LIMIT, ge=1, le=MAX_CURSOR_LIMIT, description="Items per page"),
) -> CursorPaginationParams:
    """Dependency for cursor-based pagination (mobile-safe)."""
    return CursorPaginationParams(cursor=cursor, limit=limit)

