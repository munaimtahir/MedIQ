"""Tests for questions search service and endpoints."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.core.config import settings
from app.models.question_cms import Question, QuestionStatus
from app.models.user import User, UserRole
from app.search.questions_search_service import (
    _get_allowed_statuses,
    _is_elasticsearch_available,
    search_questions_admin,
)


class TestSearchService:
    """Test search service functionality."""

    def test_get_allowed_statuses_published_only(self):
        """Test that published_only returns only PUBLISHED."""
        user = User(id=uuid4(), role=UserRole.ADMIN.value, email="admin@test.com")
        statuses = _get_allowed_statuses(user, include_unpublished=False)
        assert statuses == [QuestionStatus.PUBLISHED.value]

    def test_get_allowed_statuses_admin_all(self):
        """Test that ADMIN can see all statuses when include_unpublished=True."""
        user = User(id=uuid4(), role=UserRole.ADMIN.value, email="admin@test.com")
        statuses = _get_allowed_statuses(user, include_unpublished=True)
        assert QuestionStatus.DRAFT.value in statuses
        assert QuestionStatus.IN_REVIEW.value in statuses
        assert QuestionStatus.APPROVED.value in statuses
        assert QuestionStatus.PUBLISHED.value in statuses

    def test_get_allowed_statuses_reviewer_restricted(self):
        """Test that REVIEWER cannot see DRAFT when include_unpublished=True."""
        user = User(id=uuid4(), role=UserRole.REVIEWER.value, email="reviewer@test.com")
        statuses = _get_allowed_statuses(user, include_unpublished=True)
        assert QuestionStatus.DRAFT.value not in statuses
        assert QuestionStatus.IN_REVIEW.value in statuses
        assert QuestionStatus.APPROVED.value in statuses
        assert QuestionStatus.PUBLISHED.value in statuses

    def test_search_engine_selection_disabled(self, db, monkeypatch):
        """Test that disabled ES uses Postgres."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", False):
            user = User(id=uuid4(), role=UserRole.ADMIN.value, email="admin@test.com")
            result = search_questions_admin(db=db, user=user, page=1, page_size=10)
            assert result["engine"] == "postgres"
            assert "elasticsearch_disabled" in result["warnings"] or "elasticsearch_unreachable_fallback_postgres" in result["warnings"]

    def test_search_engine_selection_unreachable(self, db, monkeypatch):
        """Test that unreachable ES falls back to Postgres with warning."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.questions_search_service.ping", return_value=False):
                user = User(id=uuid4(), role=UserRole.ADMIN.value, email="admin@test.com")
                result = search_questions_admin(db=db, user=user, page=1, page_size=10)
                assert result["engine"] == "postgres"
                assert any("elasticsearch_unreachable_fallback_postgres" in w for w in result["warnings"])

    def test_search_response_contract(self, db):
        """Test that response always has stable contract."""
        user = User(id=uuid4(), role=UserRole.ADMIN.value, email="admin@test.com")
        result = search_questions_admin(db=db, user=user, page=1, page_size=10)

        # Check required fields
        assert "engine" in result
        assert "total" in result
        assert "page" in result
        assert "page_size" in result
        assert "results" in result
        assert "facets" in result
        assert "warnings" in result

        # Check engine is valid
        assert result["engine"] in ("elasticsearch", "postgres")

        # Check facets structure
        assert "year" in result["facets"]
        assert "block_id" in result["facets"]
        assert "theme_id" in result["facets"]
        assert "cognitive_level" in result["facets"]
        assert "difficulty_label" in result["facets"]
        assert "source_book" in result["facets"]
        assert "status" in result["facets"]

    def test_search_pagination_validation(self, db):
        """Test pagination validation."""
        user = User(id=uuid4(), role=UserRole.ADMIN.value, email="admin@test.com")
        
        # Valid pagination
        result = search_questions_admin(db=db, user=user, page=1, page_size=25)
        assert result["page"] == 1
        assert result["page_size"] == 25

        # Page 2
        result = search_questions_admin(db=db, user=user, page=2, page_size=25)
        assert result["page"] == 2

    def test_search_filters_deduplication(self, db):
        """Test that repeated filter values are deduplicated."""
        user = User(id=uuid4(), role=UserRole.ADMIN.value, email="admin@test.com")
        
        # Should not raise with duplicate values
        result = search_questions_admin(
            db=db,
            user=user,
            cognitive_level=["C1", "C2", "C1"],  # Duplicate
            page=1,
            page_size=10,
        )
        assert result["engine"] in ("elasticsearch", "postgres")
