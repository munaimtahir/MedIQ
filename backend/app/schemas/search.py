"""Pydantic schemas for search endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """Single search result item."""

    question_id: str
    version_id: str | None
    status: str
    published_at: str | None
    updated_at: str | None
    year: int | None
    block_id: str | None
    theme_id: str | None
    topic_id: str | None
    cognitive_level: str | None
    difficulty_label: str | None
    source_book: str | None
    source_page: int | None
    stem_preview: str
    explanation_preview: str
    tags_preview: str
    has_media: bool


class FacetItem(BaseModel):
    """Facet item."""

    value: str | int
    count: int


class SearchResponse(BaseModel):
    """Search response (stable contract)."""

    engine: str  # "elasticsearch" | "postgres"
    total: int
    page: int
    page_size: int
    results: list[SearchResultItem]
    facets: dict[str, list[FacetItem]]
    warnings: list[str]


class SearchMetaResponse(BaseModel):
    """Search metadata response."""

    limits: dict[str, int]
    engine: dict[str, bool]
    defaults: dict[str, Any]
    sort_options: list[str]
