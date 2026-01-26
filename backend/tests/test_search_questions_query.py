"""Tests for questions search query builder."""

import pytest

from app.search.questions_query import build_questions_search_query


class TestQuestionsQueryBuilder:
    """Test questions search query builder."""

    def test_query_with_text_search(self):
        """Test query with text search."""
        query = build_questions_search_query(q="cardiac", page=1, page_size=10)

        assert "query" in query
        assert "bool" in query["query"]
        assert "must" in query["query"]["bool"]
        must_clauses = query["query"]["bool"]["must"]

        # Should have status filter and multi_match
        assert len(must_clauses) == 2
        assert {"term": {"status": "PUBLISHED"}} in must_clauses

        multi_match = next(
            (clause for clause in must_clauses if "multi_match" in clause), None
        )
        assert multi_match is not None
        assert multi_match["multi_match"]["query"] == "cardiac"
        assert "stem^3" in multi_match["multi_match"]["fields"]

    def test_query_with_filters(self):
        """Test query with filters."""
        filters = {
            "year": 1,
            "block_id": "123",
            "theme_id": "456",
            "cognitive_level": "application",
        }
        query = build_questions_search_query(filters=filters)

        assert "query" in query
        assert "bool" in query["query"]
        assert "filter" in query["query"]["bool"]

        filter_clauses = query["query"]["bool"]["filter"]
        assert len(filter_clauses) == 4

        # Check filters are present
        filter_dict = {}
        for clause in filter_clauses:
            if "term" in clause:
                for key, value in clause["term"].items():
                    filter_dict[key] = value

        assert filter_dict.get("year") == 1
        assert filter_dict.get("block_id") == "123"
        assert filter_dict.get("theme_id") == "456"
        assert filter_dict.get("cognitive_level") == "application"

    def test_query_status_filter_published_only(self):
        """Test default status filter is PUBLISHED only."""
        query = build_questions_search_query()

        must_clauses = query["query"]["bool"]["must"]
        assert {"term": {"status": "PUBLISHED"}} in must_clauses

    def test_query_status_filter_include_approved(self):
        """Test status filter includes APPROVED when flag set."""
        query = build_questions_search_query(include_approved=True)

        must_clauses = query["query"]["bool"]["must"]
        status_filter = next(
            (clause for clause in must_clauses if "terms" in clause or "term" in clause), None
        )
        assert status_filter is not None
        if "terms" in status_filter:
            assert "PUBLISHED" in status_filter["terms"]["status"]
            assert "APPROVED" in status_filter["terms"]["status"]

    def test_query_sort_relevance(self):
        """Test relevance sort."""
        query = build_questions_search_query(q="test", sort="relevance")

        assert query["sort"] == ["_score"]

    def test_query_sort_published_at_desc(self):
        """Test published_at desc sort."""
        query = build_questions_search_query(sort="published_at_desc")

        assert query["sort"] == [{"published_at": {"order": "desc"}}]

    def test_query_sort_updated_at_desc(self):
        """Test updated_at desc sort."""
        query = build_questions_search_query(sort="updated_at_desc")

        assert query["sort"] == [{"updated_at": {"order": "desc"}}]

    def test_query_pagination(self):
        """Test pagination parameters."""
        query = build_questions_search_query(page=3, page_size=25)

        assert query["from"] == 50  # (3-1) * 25
        assert query["size"] == 25

    def test_query_empty_string_ignored(self):
        """Test empty query string is ignored."""
        query = build_questions_search_query(q="   ")

        must_clauses = query["query"]["bool"]["must"]
        # Should only have status filter, no multi_match
        assert len(must_clauses) == 1
        assert {"term": {"status": "PUBLISHED"}} in must_clauses

    def test_query_all_filters(self):
        """Test all supported filters."""
        filters = {
            "year": 2,
            "block_id": "100",
            "theme_id": "200",
            "topic_id": "300",
            "cognitive_level": "analysis",
            "difficulty_label": "hard",
            "source_book": "Gray's Anatomy",
        }
        query = build_questions_search_query(filters=filters)

        filter_clauses = query["query"]["bool"]["filter"]
        assert len(filter_clauses) == 7
