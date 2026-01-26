"""Tests for Neo4j graph schema and cypher helpers."""

import pytest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.graph.cypher import upsert_concept_node, upsert_prereq_edge, deactivate_missing_edges
from app.graph.schema import ensure_constraints_and_indexes


class TestCypherHelpers:
    """Test Cypher query builders."""

    def test_upsert_concept_node_valid(self):
        """Test upsert_concept_node with valid concept."""
        concept = {
            "concept_id": "concept-1",
            "name": "Test Concept",
            "year": 1,
            "block_id": "block-1",
            "theme_id": "theme-1",
            "topic_id": "topic-1",
            "level": "CONCEPT",
            "is_active": True,
        }

        cypher, params = upsert_concept_node(concept)

        assert "MERGE" in cypher
        assert "Concept" in cypher
        assert params["concept_id"] == "concept-1"
        assert params["name"] == "Test Concept"
        assert params["level"] == "CONCEPT"

    def test_upsert_concept_node_missing_concept_id(self):
        """Test upsert_concept_node rejects missing concept_id."""
        concept = {
            "name": "Test Concept",
        }

        with pytest.raises(ValueError, match="concept_id is required"):
            upsert_concept_node(concept)

    def test_upsert_concept_node_empty_concept_id(self):
        """Test upsert_concept_node rejects empty concept_id."""
        concept = {
            "concept_id": "",
            "name": "Test Concept",
        }

        with pytest.raises(ValueError, match="concept_id is required"):
            upsert_concept_node(concept)

    def test_upsert_prereq_edge_valid(self):
        """Test upsert_prereq_edge with valid edge."""
        props = {
            "weight": 0.8,
            "source": "MANUAL",
            "is_active": True,
            "notes": "Test edge",
        }

        cypher, params = upsert_prereq_edge("concept-1", "concept-2", props)

        assert "MERGE" in cypher
        assert "PREREQ" in cypher
        assert params["from_id"] == "concept-1"
        assert params["to_id"] == "concept-2"
        assert params["weight"] == 0.8
        assert params["source"] == "MANUAL"

    def test_upsert_prereq_edge_self_loop(self):
        """Test upsert_prereq_edge blocks self-loops."""
        with pytest.raises(ValueError, match="Self-loop edges are not allowed"):
            upsert_prereq_edge("concept-1", "concept-1")

    def test_upsert_prereq_edge_defaults(self):
        """Test upsert_prereq_edge uses defaults when props not provided."""
        cypher, params = upsert_prereq_edge("concept-1", "concept-2")

        assert params["weight"] == 1.0
        assert params["source"] == "MANUAL"
        assert params["is_active"] is True

    def test_deactivate_missing_edges_stub(self):
        """Test deactivate_missing_edges returns stub query."""
        edge_ids = [("concept-1", "concept-2"), ("concept-2", "concept-3")]

        cypher, params = deactivate_missing_edges(edge_ids)

        assert "stub" in cypher.lower() or "deactivate" in cypher.lower()
        assert params["edge_ids"] == edge_ids


class TestSchema:
    """Test schema management."""

    def test_ensure_constraints_and_indexes_disabled(self):
        """Test schema creation when Neo4j is disabled."""
        with patch.object(settings, "NEO4J_ENABLED", False):
            result = ensure_constraints_and_indexes()
            assert result["enabled"] is False
            assert len(result["constraints_created"]) == 0
            assert len(result["indexes_created"]) == 0

    def test_ensure_constraints_and_indexes_builds_cypher(self):
        """Test that schema function builds correct Cypher strings."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.schema.get_driver") as mock_driver:
                mock_driver.return_value = MagicMock()

                with patch("app.graph.schema.run_write") as mock_write:
                    ensure_constraints_and_indexes()

                    # Check that run_write was called with constraint and index queries
                    write_calls = [call[0][0] for call in mock_write.call_args_list]

                    # Should have constraint query
                    constraint_calls = [c for c in write_calls if "CONSTRAINT" in c and "concept_id_unique" in c]
                    assert len(constraint_calls) > 0

                    # Should have index queries
                    index_calls = [c for c in write_calls if "INDEX" in c]
                    assert len(index_calls) >= 3  # level, theme_id, block_id

                    # Check index names
                    index_names = []
                    for call in write_calls:
                        if "INDEX" in call:
                            # Extract index name from CREATE INDEX name_index
                            if "level_index" in call:
                                index_names.append("level")
                            if "theme_id_index" in call:
                                index_names.append("theme_id")
                            if "block_id_index" in call:
                                index_names.append("block_id")

                    assert "level" in index_names
                    assert "theme_id" in index_names
                    assert "block_id" in index_names
