"""Tests for search outbox emission."""

import pytest
from uuid import uuid4

from app.models.question_cms import Question, QuestionStatus
from app.models.search_indexing import SearchOutbox, SearchOutboxEventType
from app.search.outbox_emit import emit_search_outbox_event


class TestOutboxEmission:
    """Test outbox event emission."""

    def test_emit_publish_event(self, db):
        """Test emitting a publish event."""
        question_id = uuid4()
        version_id = uuid4()

        emit_search_outbox_event(
            db=db,
            event_type=SearchOutboxEventType.QUESTION_PUBLISHED,
            question_id=question_id,
            version_id=version_id,
        )

        event = db.query(SearchOutbox).filter(
            SearchOutbox.payload["question_id"].astext == str(question_id)
        ).first()
        assert event is not None
        assert event.event_type == SearchOutboxEventType.QUESTION_PUBLISHED
        assert event.payload["question_id"] == str(question_id)
        assert event.payload["version_id"] == str(version_id)

    def test_emit_unpublish_event(self, db):
        """Test emitting an unpublish event."""
        question_id = uuid4()

        emit_search_outbox_event(
            db=db,
            event_type=SearchOutboxEventType.QUESTION_UNPUBLISHED,
            question_id=question_id,
        )

        event = db.query(SearchOutbox).filter(
            SearchOutbox.payload["question_id"].astext == str(question_id)
        ).first()
        assert event is not None
        assert event.event_type == SearchOutboxEventType.QUESTION_UNPUBLISHED
        assert "version_id" not in event.payload

    def test_emit_fails_open_on_error(self, db, monkeypatch):
        """Test that emission fails open (doesn't raise)."""
        question_id = uuid4()

        # Mock db.commit to raise
        def mock_commit():
            raise Exception("DB error")

        monkeypatch.setattr(db, "commit", mock_commit)

        # Should not raise
        emit_search_outbox_event(
            db=db,
            event_type=SearchOutboxEventType.QUESTION_PUBLISHED,
            question_id=question_id,
        )

        # Event should not be created (or should be rolled back)
        event = db.query(SearchOutbox).filter(
            SearchOutbox.payload["question_id"].astext == str(question_id)
        ).first()
        assert event is None
