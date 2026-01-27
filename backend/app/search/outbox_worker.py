"""Outbox worker for processing search indexing events."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from elasticsearch.exceptions import ConnectionError, RequestError, TransportError
from sqlalchemy import and_, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.algo_runtime import AlgoRuntimeConfig
from app.models.question_cms import Question, QuestionStatus
from app.models.search_indexing import (
    SearchOutbox,
    SearchOutboxEventType,
    SearchOutboxStatus,
)
from app.search.document_builder import build_question_document
from app.search.es_client import get_es_client
from app.search.index_bootstrap import (
    ensure_questions_aliases_exist,
    get_questions_write_alias,
)

logger = logging.getLogger(__name__)


def calculate_next_attempt(retry_count: int) -> datetime:
    """
    Calculate next attempt time with exponential backoff.

    Args:
        retry_count: Current retry count

    Returns:
        Next attempt datetime
    """
    # Exponential backoff: 2^retry_count minutes, max 24 hours
    minutes = min(2 ** retry_count, 1440)  # 1440 minutes = 24 hours
    return datetime.now(UTC) + timedelta(minutes=minutes)


def fetch_pending_events(db: Session, limit: int = 100) -> list[SearchOutbox]:
    """
    Fetch pending events with FOR UPDATE SKIP LOCKED.

    Args:
        db: Database session
        limit: Maximum number of events to fetch

    Returns:
        List of pending events
    """
    now = datetime.now(UTC)
    
    events = (
        db.query(SearchOutbox)
        .filter(
            and_(
                SearchOutbox.status == SearchOutboxStatus.PENDING,
                (SearchOutbox.next_attempt_at.is_(None)) | (SearchOutbox.next_attempt_at <= now),
            )
        )
        .order_by(SearchOutbox.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(limit)
        .all()
    )
    
    return events


def mark_event_processing(db: Session, event: SearchOutbox) -> None:
    """Mark event as processing."""
    event.status = SearchOutboxStatus.PROCESSING.value
    event.updated_at = datetime.now(UTC)
    db.commit()


def mark_event_done(db: Session, event: SearchOutbox) -> None:
    """Mark event as done."""
    event.status = SearchOutboxStatus.DONE.value
    event.updated_at = datetime.now(UTC)
    db.commit()


def mark_event_failed(
    db: Session,
    event: SearchOutbox,
    error: str,
    retry: bool = True,
) -> None:
    """
    Mark event as failed and schedule retry if applicable.

    Args:
        db: Database session
        event: Event to mark
        error: Error message
        retry: Whether to schedule a retry
    """
    event.status = SearchOutboxStatus.FAILED.value
    event.last_error = error[:1000]  # Truncate to 1000 chars
    event.retry_count += 1
    event.updated_at = datetime.now(UTC)

    if retry and event.retry_count < 10:  # Max 10 retries
        event.status = SearchOutboxStatus.PENDING.value
        event.next_attempt_at = calculate_next_attempt(event.retry_count)
        logger.warning(
            f"Scheduling retry {event.retry_count} for event {event.id} at {event.next_attempt_at}"
        )
    else:
        logger.error(
            f"Event {event.id} failed permanently after {event.retry_count} retries: {error}"
        )

    db.commit()


def check_freeze_updates(db: Session) -> bool:
    """
    Check if freeze_updates is enabled (sync version).

    Args:
        db: Database session

    Returns:
        True if frozen, False otherwise
    """
    try:
        config = db.query(AlgoRuntimeConfig).limit(1).first()
        if not config:
            return False
        config_json = config.config_json or {}
        safe_mode = config_json.get("safe_mode", {})
        return safe_mode.get("freeze_updates", False)
    except Exception as e:
        logger.warning(f"Failed to check freeze_updates: {e}")
        # Fail-open: assume not frozen if check fails
        return False


def process_event(db: Session, event: SearchOutbox) -> None:
    """
    Process a single outbox event.

    Args:
        db: Database session
        event: Event to process
    """
    try:
        # Check if ES is enabled
        if not settings.ELASTICSEARCH_ENABLED:
            logger.debug("Elasticsearch disabled, skipping event processing")
            mark_event_done(db, event)
            return

        # Ensure aliases exist
        try:
            ensure_questions_aliases_exist()
        except Exception as e:
            logger.warning(f"Failed to ensure aliases exist: {e}")
            mark_event_failed(db, event, f"Alias check failed: {str(e)}", retry=True)
            return

        # Get ES client
        client = get_es_client()
        if client is None:
            mark_event_failed(db, event, "Elasticsearch client unavailable", retry=True)
            return

        # Get write alias
        write_alias = get_questions_write_alias()

        # Extract payload
        question_id_str = event.payload.get("question_id")
        if not question_id_str:
            mark_event_failed(db, event, "Missing question_id in payload", retry=False)
            return

        question_id = UUID(question_id_str)
        version_id_str = event.payload.get("version_id")

        # Process based on event type
        if event.event_type == SearchOutboxEventType.QUESTION_PUBLISHED:
            # Upsert document
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                mark_event_failed(db, event, f"Question {question_id} not found", retry=False)
                return

            if question.status != QuestionStatus.PUBLISHED:
                # Question is no longer published, skip
                mark_event_done(db, event)
                return

            doc = build_question_document(db, question)
            if not doc:
                mark_event_failed(db, event, "Failed to build document", retry=False)
                return

            # Upsert to ES
            doc_id = f"{question_id}:{doc['version_id']}"
            try:
                client.index(index=write_alias, id=doc_id, document=doc)
                logger.debug(f"Indexed question {question_id} version {doc['version_id']}")
                mark_event_done(db, event)
            except (ConnectionError, TransportError, RequestError) as e:
                mark_event_failed(db, event, f"ES index failed: {str(e)}", retry=True)

        elif event.event_type == SearchOutboxEventType.QUESTION_UPDATED:
            # Upsert document (same as published)
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                mark_event_failed(db, event, f"Question {question_id} not found", retry=False)
                return

            if question.status != QuestionStatus.PUBLISHED:
                # Question is no longer published, delete from index
                if version_id_str:
                    doc_id = f"{question_id}:{version_id_str}"
                else:
                    # Delete all versions of this question
                    doc_id = f"{question_id}:*"
                
                try:
                    if "*" in doc_id:
                        # Delete by query
                        client.delete_by_query(
                            index=write_alias,
                            body={"query": {"term": {"question_id": str(question_id)}}},
                        )
                    else:
                        client.delete(index=write_alias, id=doc_id, ignore=[404])
                    mark_event_done(db, event)
                except (ConnectionError, TransportError, RequestError) as e:
                    mark_event_failed(db, event, f"ES delete failed: {str(e)}", retry=True)
                return

            doc = build_question_document(db, question)
            if not doc:
                mark_event_failed(db, event, "Failed to build document", retry=False)
                return

            doc_id = f"{question_id}:{doc['version_id']}"
            try:
                client.index(index=write_alias, id=doc_id, document=doc)
                logger.debug(f"Updated question {question_id} version {doc['version_id']}")
                mark_event_done(db, event)
            except (ConnectionError, TransportError, RequestError) as e:
                mark_event_failed(db, event, f"ES index failed: {str(e)}", retry=True)

        elif event.event_type == SearchOutboxEventType.QUESTION_UNPUBLISHED:
            # Delete document
            if version_id_str:
                doc_id = f"{question_id}:{version_id_str}"
            else:
                # Delete all versions of this question
                doc_id = f"{question_id}:*"

            try:
                if "*" in doc_id:
                    # Delete by query
                    client.delete_by_query(
                        index=write_alias,
                        body={"query": {"term": {"question_id": str(question_id)}}},
                    )
                else:
                    client.delete(index=write_alias, id=doc_id, ignore=[404])
                logger.debug(f"Deleted question {question_id} from index")
                mark_event_done(db, event)
            except (ConnectionError, TransportError, RequestError) as e:
                mark_event_failed(db, event, f"ES delete failed: {str(e)}", retry=True)

        elif event.event_type == SearchOutboxEventType.QUESTION_DELETED:
            # Delete all versions of this question
            try:
                client.delete_by_query(
                    index=write_alias,
                    body={"query": {"term": {"question_id": str(question_id)}}},
                )
                logger.debug(f"Deleted question {question_id} from index")
                mark_event_done(db, event)
            except (ConnectionError, TransportError, RequestError) as e:
                mark_event_failed(db, event, f"ES delete failed: {str(e)}", retry=True)

        else:
            mark_event_failed(db, event, f"Unknown event type: {event.event_type}", retry=False)

    except Exception as e:
        logger.error(f"Unexpected error processing event {event.id}: {e}", exc_info=True)
        mark_event_failed(db, event, f"Unexpected error: {str(e)}", retry=True)


def process_outbox_batch(db: Session, limit: int = 100) -> dict[str, Any]:
    """
    Process a batch of outbox events.

    Args:
        db: Database session
        limit: Maximum number of events to process

    Returns:
        Dictionary with processing stats
    """
    # Check freeze_updates
    frozen = check_freeze_updates(db)
    
    if frozen:
        logger.info("freeze_updates is enabled, skipping outbox processing")
        return {
            "processed": 0,
            "done": 0,
            "failed": 0,
            "frozen": True,
        }

    # Fetch pending events
    events = fetch_pending_events(db, limit)
    
    if not events:
        return {
            "processed": 0,
            "done": 0,
            "failed": 0,
            "frozen": False,
        }

    processed = 0
    done = 0
    failed = 0

    for event in events:
        try:
            mark_event_processing(db, event)
            process_event(db, event)
            processed += 1
            
            # Check final status
            db.refresh(event)
            if event.status == SearchOutboxStatus.DONE:
                done += 1
            elif event.status == SearchOutboxStatus.FAILED:
                failed += 1
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {e}", exc_info=True)
            try:
                mark_event_failed(db, event, f"Processing error: {str(e)}", retry=True)
                failed += 1
            except Exception:
                pass

    return {
        "processed": processed,
        "done": done,
        "failed": failed,
        "frozen": False,
    }
