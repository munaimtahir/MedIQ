"""Schemas for offline sync (mobile batch operations)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SyncAttemptItem(BaseModel):
    """Single attempt item in batch sync request."""

    client_attempt_id: UUID = Field(..., description="Client-generated attempt ID")
    idempotency_key: UUID = Field(..., description="Idempotency key for this attempt")
    session_id: UUID | None = Field(None, description="Server session ID (if exists)")
    offline_session_id: UUID | None = Field(None, description="Client-generated offline session ID")
    question_id: UUID = Field(..., description="Question ID")
    selected_option_index: int = Field(..., ge=0, le=4, description="Selected option index (0-4)")
    answered_at: datetime = Field(..., description="Client timestamp (ISO-8601 UTC)")
    payload_hash: str = Field(..., description="SHA-256 hash of attempt payload for idempotency")


class BatchSyncRequest(BaseModel):
    """Batch sync request for offline attempts."""

    attempts: list[SyncAttemptItem] = Field(..., min_length=1, max_length=100, description="List of attempts to sync")


class SyncAttemptResult(BaseModel):
    """Result for a single attempt in batch sync."""

    client_attempt_id: UUID
    status: Literal["acked", "duplicate", "rejected"]
    error_code: str | None = None
    message: str | None = None
    server_attempt_id: UUID | None = None
    server_session_id: UUID | None = None


class BatchSyncResponse(BaseModel):
    """Response for batch sync endpoint."""

    results: list[SyncAttemptResult]
