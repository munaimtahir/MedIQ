"""Warehouse export row contracts (stable Pydantic schemas).

These contracts define the exact shape of data exported to Snowflake.
Contracts must remain stable - changes require versioning.
"""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ExportEnvelope(BaseModel):
    """Shared metadata envelope for all export rows."""

    export_version: str = Field(default="1.0", description="Export schema version")
    generated_at: datetime = Field(description="Timestamp when export was generated")
    source_commit: Optional[str] = Field(default=None, description="Git commit hash (optional)")


class AttemptExportRow(BaseModel):
    """FACT_ATTEMPT export row contract."""

    # Required fields
    attempt_id: str = Field(description="Unique attempt identifier (session_answer.id)")
    user_id: str = Field(description="User UUID")
    session_id: str = Field(description="Test session UUID")
    question_id: str = Field(description="Question UUID")
    attempted_at: datetime = Field(description="Timestamp when attempt was made")
    is_correct: bool = Field(description="Whether the answer was correct")

    # Optional but included if available
    concept_id: Optional[int] = Field(default=None, description="Concept ID (if available)")
    theme_id: Optional[int] = Field(default=None, description="Theme ID")
    block_id: Optional[int] = Field(default=None, description="Block ID")
    year: Optional[int] = Field(default=None, description="Year number")

    # Answer details
    selected_index: Optional[int] = Field(default=None, description="Selected option index (0-4)")
    correct_index: Optional[int] = Field(default=None, description="Correct option index (0-4)")
    time_spent_ms: Optional[int] = Field(default=None, description="Time spent in milliseconds")
    changed_answer_count: Optional[int] = Field(default=None, description="Number of times answer was changed")
    marked_for_review: Optional[bool] = Field(default=None, description="Whether marked for review")

    # Difficulty snapshot (at attempt time)
    difficulty_snapshot: Optional[str] = Field(default=None, description="Difficulty label (e.g., 'EASY', 'MEDIUM')")
    difficulty_value: Optional[float] = Field(default=None, description="Difficulty numeric value (if available)")

    # ELO ratings (at attempt time)
    elo_user_before: Optional[float] = Field(default=None, description="User ELO before attempt")
    elo_user_after: Optional[float] = Field(default=None, description="User ELO after attempt")
    elo_question_before: Optional[float] = Field(default=None, description="Question ELO before attempt")
    elo_question_after: Optional[float] = Field(default=None, description="Question ELO after attempt")

    # Algorithm metadata (snapshot at attempt time)
    algo_profile: str = Field(description="Algorithm profile (e.g., 'V1_PRIMARY', 'V0_FALLBACK')")
    algo_versions: dict[str, Any] = Field(
        default_factory=dict,
        description="Algorithm version snapshot: {mastery: 'v1', revision: 'v1', adaptive: 'v1', difficulty: 'v1', mistakes: 'v1'}",
    )


class EventExportRow(BaseModel):
    """FACT_EVENT export row contract."""

    # Required fields
    event_id: str = Field(description="Unique event identifier (attempt_events.id)")
    user_id: str = Field(description="User UUID")
    session_id: str = Field(description="Test session UUID")
    event_type: str = Field(description="Event type (e.g., 'answer_submitted', 'question_viewed')")
    event_at: datetime = Field(description="Event timestamp")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event-specific payload data")
    client_meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Client metadata (source, client_ts, seq, etc.)",
    )
    ingested_at: datetime = Field(description="Timestamp when event was ingested into database")


class MasterySnapshotExportRow(BaseModel):
    """SNAPSHOT_MASTERY export row contract."""

    # Required fields
    snapshot_id: str = Field(description="Unique snapshot identifier")
    user_id: str = Field(description="User UUID")
    concept_id: str = Field(description="Concept identifier (theme_id as concept_id for v1)")
    snapshot_at: datetime = Field(description="Snapshot timestamp")

    # Mastery metrics
    mastery_prob: float = Field(description="Mastery probability (0.0 to 1.0)")
    attempts_total: int = Field(description="Total attempts for this concept")
    correct_total: int = Field(description="Total correct attempts")
    last_attempt_at: Optional[datetime] = Field(default=None, description="Last attempt timestamp")

    # BKT parameters (if available)
    bkt_params: dict[str, Any] = Field(
        default_factory=dict,
        description="BKT parameters: {p_init, p_learn, p_guess, p_slip} or empty if not BKT",
    )

    # Algorithm metadata
    algo_profile: str = Field(description="Algorithm profile used for mastery computation")
    algo_version_mastery: str = Field(description="Mastery algorithm version (e.g., 'bkt_v1', 'fsrs_v1')")


class RevisionQueueDailyExportRow(BaseModel):
    """SNAPSHOT_REVISION_QUEUE_DAILY export row contract."""

    # Required fields
    snapshot_date: date = Field(description="Snapshot date (YYYY-MM-DD)")
    user_id: str = Field(description="User UUID")
    due_today_count: int = Field(description="Number of items due today")
    overdue_count: int = Field(description="Number of overdue items")
    next_due_at: Optional[datetime] = Field(default=None, description="Next due item timestamp")

    # Algorithm metadata
    algo_profile: str = Field(description="Algorithm profile used for revision scheduling")
    algo_version_revision: str = Field(description="Revision algorithm version (e.g., 'fsrs_v1', 'srs_v0')")
