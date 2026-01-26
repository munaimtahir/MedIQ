"""Tests for Neo4j graph health endpoint."""

import pytest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.graph.health import get_graph_health
from app.graph.neo4j_client import ping, run_read


class TestGraphHealth:
    """Test graph health check."""

    def test_health_disabled(self):
        """Test health returns enabled=false when Neo4j is disabled."""
        with patch.object(settings, "NEO4J_ENABLED", False):
            health = get_graph_health()

            assert health["enabled"] is False
            assert health["reachable"] is False
            assert health["latency_ms"] is None
            assert health["schema_ok"] is False
            assert health["node_count"] is None
            assert health["edge_count"] is None

    def test_health_enabled_unreachable(self):
        """Test health when Neo4j is enabled but unreachable."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.health.ping", return_value=(False, None, {"error": "connection_failed"})):
                health = get_graph_health()

                assert health["enabled"] is True
                assert health["reachable"] is False
                assert health["latency_ms"] is None
                assert health["schema_ok"] is False
                assert "error" in health

    def test_health_enabled_reachable(self):
        """Test health when Neo4j is enabled and reachable."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.health.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                with patch("app.graph.health.ensure_constraints_and_indexes", return_value={
                    "enabled": True,
                    "constraints_created": ["concept_id_unique"],
                    "indexes_created": ["level_index"],
                }):
                    with patch("app.graph.health.run_read") as mock_read:
                        # Mock node and edge counts
                        mock_read.side_effect = [
                            [{"count": 100}],  # node count
                            [{"count": 50}],  # edge count
                        ]

                        health = get_graph_health()

                        assert health["enabled"] is True
                        assert health["reachable"] is True
                        assert health["latency_ms"] == 10
                        assert health["schema_ok"] is True
                        assert health["node_count"] == 100
                        assert health["edge_count"] == 50
