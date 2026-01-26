"""Pydantic schemas for telemetry events."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# Event Types Enum
# ============================================================================


class EventType(str, PyEnum):
    """Allowed telemetry event types."""

    # Session lifecycle
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_SUBMITTED = "SESSION_SUBMITTED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    REVIEW_OPENED = "REVIEW_OPENED"

    # Navigation
    QUESTION_VIEWED = "QUESTION_VIEWED"
    NAVIGATE_NEXT = "NAVIGATE_NEXT"
    NAVIGATE_PREV = "NAVIGATE_PREV"
    NAVIGATE_JUMP = "NAVIGATE_JUMP"

    # Answer interactions
    ANSWER_SELECTED = "ANSWER_SELECTED"
    ANSWER_CHANGED = "ANSWER_CHANGED"
    MARK_FOR_REVIEW_TOGGLED = "MARK_FOR_REVIEW_TOGGLED"

    # Behavioral
    PAUSE_BLUR = "PAUSE_BLUR"


# ============================================================================
# Request/Response Schemas
# ============================================================================


class TelemetryEventSubmit(BaseModel):
    """Single telemetry event from client."""

    event_type: EventType = Field(..., description="Event type")
    client_ts: datetime | None = Field(None, description="Client-side timestamp")
    seq: int | None = Field(None, description="Client sequence number")
    session_id: UUID = Field(..., description="Session ID")
    question_id: UUID | None = Field(None, description="Question ID (optional)")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event-specific payload")

    @field_validator("payload")
    @classmethod
    def validate_payload_size(cls, v):
        """Ensure payload is not too large."""
        import json

        payload_str = json.dumps(v)
        if len(payload_str) > 4096:  # 4KB limit
            raise ValueError("Payload exceeds 4KB limit")
        return v


class TelemetryBatchSubmit(BaseModel):
    """Batch of telemetry events from client."""

    source: str = Field("web", description="Event source (web, mobile, api)")
    events: list[TelemetryEventSubmit] = Field(..., description="List of events", max_length=50)

    @field_validator("events")
    @classmethod
    def validate_batch_size(cls, v):
        """Ensure batch is not too large."""
        if len(v) > 50:
            raise ValueError("Batch size exceeds 50 events")
        return v


class TelemetryBatchResponse(BaseModel):
    """Response after processing telemetry batch."""

    accepted: int = Field(..., description="Number of accepted events")
    rejected: int = Field(..., description="Number of rejected events")
    rejected_reasons_sample: list[str] = Field(
        default_factory=list, description="Sample of rejection reasons (max 5)"
    )


class TelemetryEventOut(BaseModel):
    """Telemetry event response."""

    id: UUID
    event_version: int
    event_type: str
    event_ts: datetime
    client_ts: datetime | None
    seq: int | None
    session_id: UUID
    user_id: UUID
    question_id: UUID | None
    source: str | None
    payload_json: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Payload Documentation (for reference)
# ============================================================================

"""
Expected payload shapes by event type:

SESSION_CREATED:
    {
        "mode": "TUTOR" | "EXAM",
        "filters": {...},
        "count": number
    }

QUESTION_VIEWED:
    {
        "position": number
    }

NAVIGATE_NEXT / NAVIGATE_PREV:
    {
        "from_position": number,
        "to_position": number
    }

NAVIGATE_JUMP:
    {
        "from_position": number,
        "to_position": number
    }

ANSWER_SELECTED:
    {
        "position": number,
        "selected_index": number
    }

ANSWER_CHANGED:
    {
        "position": number,
        "from_index": number,
        "to_index": number
    }

MARK_FOR_REVIEW_TOGGLED:
    {
        "position": number,
        "marked": boolean
    }

SESSION_SUBMITTED:
    {
        "reason": "manual" | "expired"
    }

SESSION_EXPIRED:
    {}

REVIEW_OPENED:
    {}

PAUSE_BLUR:
    {
        "state": "blur" | "focus"
    }

NOTE: These are guidelines. Telemetry is best-effort and payloads should remain small.
"""
