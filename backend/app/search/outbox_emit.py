"""Outbox event emission for search indexing (fail-open)."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.search_indexing import SearchOutbox, SearchOutboxEventType

logger = logging.getLogger(__name__)


def emit_search_outbox_event(
    db: Session,
    event_type: SearchOutboxEventType,
    question_id: UUID,
    version_id: UUID | None = None,
) -> None:
    """
    Emit a search outbox event (fail-open).

    This function should be called AFTER the main transaction commits.
    If outbox insertion fails, it logs an error but does not raise.

    Args:
        db: Database session (should be a new session after commit)
        event_type: Type of event
        question_id: Question ID
        version_id: Optional version ID (for published versions)
    """
    try:
        payload: dict[str, Any] = {"question_id": str(question_id)}
        if version_id:
            payload["version_id"] = str(version_id)

        event = SearchOutbox(
            event_type=event_type,
            payload=payload,
        )
        db.add(event)
        db.commit()
        logger.debug(f"Emitted search outbox event: {event_type.value} for question {question_id}")
    except SQLAlchemyError as e:
        logger.error(f"Failed to emit search outbox event {event_type.value} for question {question_id}: {e}", exc_info=True)
        db.rollback()
        # Do not raise - fail-open design
    except Exception as e:
        logger.error(f"Unexpected error emitting search outbox event: {e}", exc_info=True)
        db.rollback()
        # Do not raise - fail-open design
