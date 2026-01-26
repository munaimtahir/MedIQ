"""Pydantic schemas for analytics."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Analytics Response Schemas
# ============================================================================


class BlockSummary(BaseModel):
    """Block analytics summary."""

    block_id: int
    block_name: str
    attempted: int
    correct: int
    accuracy_pct: float


class ThemeSummary(BaseModel):
    """Theme analytics summary."""

    theme_id: int
    theme_name: str
    attempted: int
    correct: int
    accuracy_pct: float


class DailyTrend(BaseModel):
    """Daily trend data point."""

    date: date
    attempted: int
    correct: int
    accuracy_pct: float


class LastSessionSummary(BaseModel):
    """Last session summary."""

    session_id: UUID
    score_pct: float
    submitted_at: datetime


class AnalyticsOverview(BaseModel):
    """Student analytics overview."""

    # Overall stats
    sessions_completed: int
    questions_seen: int
    questions_answered: int
    correct: int
    accuracy_pct: float
    avg_time_sec_per_question: float | None

    # Breakdowns
    by_block: list[BlockSummary]
    weakest_themes: list[ThemeSummary]

    # Trend (last 90 days)
    trend: list[DailyTrend]

    # Last session
    last_session: LastSessionSummary | None


class BlockAnalytics(BaseModel):
    """Block-specific analytics."""

    block_id: int
    block_name: str

    # Totals
    attempted: int
    correct: int
    accuracy_pct: float

    # Themes in this block
    themes: list[ThemeSummary]

    # Trend (last 90 days)
    trend: list[DailyTrend]


class ThemeAnalytics(BaseModel):
    """Theme-specific analytics."""

    theme_id: int
    theme_name: str
    block_id: int
    block_name: str

    # Totals
    attempted: int
    correct: int
    accuracy_pct: float

    # Trend (last 90 days)
    trend: list[DailyTrend]

    # Placeholder for future
    common_mistakes: list[Any] = Field(default_factory=list)


class RecentSessionSummary(BaseModel):
    """Recent session summary for dashboard."""

    session_id: UUID
    title: str
    status: str  # "completed" | "in_progress" | "abandoned"
    score_correct: int | None
    score_total: int | None
    score_pct: float | None
    block_id: int | None
    theme_id: int | None
    started_at: datetime
    submitted_at: datetime | None


class RecentSessionsResponse(BaseModel):
    """Recent sessions response."""

    sessions: list[RecentSessionSummary]
