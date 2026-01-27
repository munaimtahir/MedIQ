"""Tests for search outbox worker."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.core.config import settings
from app.models.question_cms import Question, QuestionStatus
from app.models.search_indexing import (
    SearchOutbox,
    SearchOutboxEventType,
    SearchOutboxStatus,
)
from app.search.outbox_worker import (
    calculate_next_attempt,
    fetch_pending_events,
    process_outbox_batch,
)


class TestOutboxWorker:
    """Test outbox worker functionality."""

    def test_calculate_next_attempt_exponential_backoff(self):
        """Test exponential backoff calculation."""
        attempt1 = calculate_next_attempt(0)
        attempt2 = calculate_next_attempt(1)
        attempt3 = calculate_next_attempt(2)

        # Should increase with retry count
        assert attempt2 > attempt1
        assert attempt3 > attempt2

    def test_fetch_pending_events(self, db):
        """Test fetching pending events with SKIP LOCKED."""
        # Create some pending events
        event1 = SearchOutbox(
            event_type=SearchOutboxEventType.QUESTION_PUBLISHED.value,
            payload={"question_id": str(uuid4())},
            status=SearchOutboxStatus.PENDING.value,
        )
        event2 = SearchOutbox(
            event_type=SearchOutboxEventType.QUESTION_UNPUBLISHED.value,
            payload={"question_id": str(uuid4())},
            status=SearchOutboxStatus.PENDING.value,
        )
        db.add(event1)
        db.add(event2)
        db.commit()

        events = fetch_pending_events(db, limit=10)
        assert len(events) == 2

    def test_process_outbox_batch_respects_freeze_updates(self, db, monkeypatch):
        """Test that processing respects freeze_updates."""
        # Mock freeze_updates to return True
        def mock_check_freeze():
            return True

        with patch("app.search.outbox_worker.check_freeze_updates", return_value=True):
            result = process_outbox_batch(db, limit=10)
            assert result["frozen"] is True
            assert result["processed"] == 0

    def test_process_outbox_batch_skips_when_es_disabled(self, db, monkeypatch):
        """Test that processing skips when ES is disabled."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", False):
            result = process_outbox_batch(db, limit=10)
            assert result["processed"] == 0
