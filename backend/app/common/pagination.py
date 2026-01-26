"""Pagination helpers (guardrails for admin performance)."""

from __future__ import annotations

from typing import Generic, TypeVar

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


def pagination_params(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, description="Page size (max 100)"),
) -> PaginationParams:
    if page_size > MAX_PAGE_SIZE:
        raise HTTPException(status_code=400, detail=f"page_size must be <= {MAX_PAGE_SIZE}")
    return PaginationParams(page=page, page_size=page_size)

