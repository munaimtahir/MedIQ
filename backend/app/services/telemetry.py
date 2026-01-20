"""Telemetry service for logging test session events.

IMPORTANT: All telemetry operations are best-effort. Failures must NOT break the main application flow.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import AttemptEvent
from app.schemas.telemetry import EventType

logger = logging.getLogger(__name__)


async def log_event(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
    event_type: EventType | str,
    payload: dict[str, Any] | None = None,
    question_id: UUID | None = None,
    source: str = "api",
    client_ts: datetime | None = None,
    seq: int | None = None,
) -> AttemptEvent | None:
    """
    Log a single telemetry event (best-effort).

    Args:
        db: Database session
        session_id: Test session ID
        user_id: User ID
        event_type: Event type
        payload: Event payload
        question_id: Question ID (optional)
        source: Event source (api, web, mobile)
        client_ts: Client timestamp (optional)
        seq: Client sequence number (optional)

    Returns:
        Created event or None if failed
    """
    try:
        # Convert enum to string if needed
        event_type_str = event_type.value if isinstance(event_type, EventType) else event_type

        event = AttemptEvent(
            session_id=session_id,
            user_id=user_id,
            event_type=event_type_str,
            event_ts=datetime.utcnow(),
            client_ts=client_ts,
            seq=seq,
            question_id=question_id,
            source=source,
            payload_json=payload or {},
        )
        db.add(event)
        # Note: Caller should commit. We don't commit here to allow batching.
        return event
    except Exception as e:
        # Best-effort: log error but don't raise
        logger.error(f"Failed to log telemetry event {event_type}: {e}", exc_info=True)
        return None


async def log_events_bulk(
    db: AsyncSession,
    user_id: UUID,
    events: list[dict[str, Any]],
    source: str = "api",
) -> tuple[int, int]:
    """
    Log multiple telemetry events in bulk (best-effort).

    Args:
        db: Database session
        user_id: User ID
        events: List of event dicts with keys: session_id, event_type, payload, etc.
        source: Event source

    Returns:
        Tuple of (accepted_count, rejected_count)
    """
    accepted = 0
    rejected = 0

    for event_data in events:
        try:
            event = AttemptEvent(
                session_id=event_data.get("session_id"),
                user_id=user_id,
                event_type=event_data.get("event_type"),
                event_ts=datetime.utcnow(),
                client_ts=event_data.get("client_ts"),
                seq=event_data.get("seq"),
                question_id=event_data.get("question_id"),
                source=source,
                payload_json=event_data.get("payload", {}),
            )
            db.add(event)
            accepted += 1
        except Exception as e:
            logger.warning(f"Rejected telemetry event: {e}")
            rejected += 1

    # Note: Caller should commit
    return accepted, rejected
