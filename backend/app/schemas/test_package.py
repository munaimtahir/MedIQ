"""Schemas for Test Packages (offline mobile caching)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class QuestionSnapshot(BaseModel):
    """Frozen question snapshot for offline use."""

    question_id: UUID
    stem: str
    option_a: str | None
    option_b: str | None
    option_c: str | None
    option_d: str | None
    option_e: str | None
    correct_index: int  # 0-4
    explanation_md: str | None
    year_id: int | None
    block_id: int | None
    theme_id: int | None
    cognitive_level: str | None
    difficulty: str | None


class PackageScopeData(BaseModel):
    """Scope data for package filtering."""

    year_id: int | None = None
    block_id: int | None = None
    theme_id: int | None = None


class TestPackageListItem(BaseModel):
    """Test package list item (summary)."""

    package_id: UUID
    name: str
    scope: str
    scope_data: PackageScopeData
    version: int
    version_hash: str
    updated_at: datetime


class TestPackageOut(BaseModel):
    """Full test package for download."""

    package_id: UUID
    name: str
    description: str | None
    scope: str
    scope_data: PackageScopeData
    version: int
    version_hash: str
    questions: list[QuestionSnapshot]
    created_at: datetime
    updated_at: datetime | None
    published_at: datetime | None


class TestPackageListResponse(BaseModel):
    """Response for package list endpoint."""

    items: list[TestPackageListItem]
