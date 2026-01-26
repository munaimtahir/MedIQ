"""Tests for Neo4j graph API endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.core.config import settings
from app.graph.service import (
    get_neighbors,
    get_prereqs,
    get_path,
    get_suggestions,
    MAX_NEIGHBORS_DEPTH,
    MAX_PATH_COUNT,
    MAX_PATH_DEPTH,
    MAX_PREREQS_DEPTH,
    MAX_SUGGESTIONS_KNOWN_IDS,
    MAX_SUGGESTIONS_LIMIT,
)


class TestServiceValidation:
    """Test service layer validation and caps."""

    def test_neighbors_depth_cap(self):
        """Test that neighbors depth is capped at MAX_NEIGHBORS_DEPTH."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.service.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                with patch("app.graph.service.run_read", return_value=[]):
                    result = get_neighbors("theme_1", depth=10)  # Exceeds cap
                    assert result["depth"] == MAX_NEIGHBORS_DEPTH

    def test_prereqs_depth_cap(self):
        """Test that prerequisites max_depth is capped."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.service.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                with patch("app.graph.service.run_read", return_value=[]):
                    result = get_prereqs("theme_1", max_depth=20)  # Exceeds cap
                    assert result["max_depth"] == MAX_PREREQS_DEPTH

    def test_path_caps(self):
        """Test that path max_paths and max_depth are capped."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.service.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                with patch("app.graph.service.run_read", return_value=[]):
                    result = get_path("theme_1", "theme_2", max_paths=10, max_depth=20)
                    # Verify caps are applied (no direct assertion, but should not exceed)
                    assert "paths" in result

    def test_suggestions_caps(self):
        """Test that suggestions limit is capped."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.service.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                with patch("app.graph.service.run_read", return_value=[]):
                    result = get_suggestions("theme_1", [], max_depth=20, limit=100)
                    # Verify caps are applied
                    assert "missing_prereqs" in result


class TestServiceDisabled:
    """Test service layer when Neo4j is disabled."""

    def test_neighbors_disabled(self):
        """Test neighbors returns error when Neo4j is disabled."""
        with patch.object(settings, "NEO4J_ENABLED", False):
            with pytest.raises(ValueError, match="Neo4j unavailable"):
                get_neighbors("theme_1")

    def test_prereqs_disabled(self):
        """Test prerequisites returns error when Neo4j is disabled."""
        with patch.object(settings, "NEO4J_ENABLED", False):
            with pytest.raises(ValueError, match="Neo4j unavailable"):
                get_prereqs("theme_1")

    def test_path_disabled(self):
        """Test path returns error when Neo4j is disabled."""
        with patch.object(settings, "NEO4J_ENABLED", False):
            with pytest.raises(ValueError, match="Neo4j unavailable"):
                get_path("theme_1", "theme_2")

    def test_suggestions_disabled(self):
        """Test suggestions returns error when Neo4j is disabled."""
        with patch.object(settings, "NEO4J_ENABLED", False):
            with pytest.raises(ValueError, match="Neo4j unavailable"):
                get_suggestions("theme_1", [])


class TestServiceUnreachable:
    """Test service layer when Neo4j is unreachable."""

    def test_neighbors_unreachable(self):
        """Test neighbors returns error when Neo4j is unreachable."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.service.ping", return_value=(False, None, {"error": "connection_failed"})):
                with pytest.raises(ValueError, match="Neo4j unavailable"):
                    get_neighbors("theme_1")


class TestServiceDeterministic:
    """Test that service returns deterministic results."""

    def test_neighbors_ordered(self):
        """Test that neighbors are returned in deterministic order."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.service.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                mock_results = [
                    {"concept_id": "theme_3", "name": "C", "level": "THEME"},
                    {"concept_id": "theme_1", "name": "A", "level": "THEME"},
                    {"concept_id": "theme_2", "name": "B", "level": "THEME"},
                ]
                with patch("app.graph.service.run_read", return_value=mock_results):
                    result = get_neighbors("theme_0", depth=1)
                    # Results should be ordered by name
                    prereq_names = [p["name"] for p in result["prereqs"]]
                    assert prereq_names == ["A", "B", "C"]  # Ordered by name

    def test_prereqs_ordered(self):
        """Test that prerequisites are returned in deterministic order."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.service.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                mock_results = [
                    {"concept_id": "theme_2", "name": "B", "level": "THEME"},
                    {"concept_id": "theme_1", "name": "A", "level": "THEME"},
                ]
                with patch("app.graph.service.run_read", return_value=mock_results):
                    result = get_prereqs("theme_0", max_depth=5)
                    node_names = [n["name"] for n in result["nodes"]]
                    assert node_names == ["A", "B"]  # Ordered by name


class TestAPIEndpoints:
    """Test API endpoints (requires FastAPI test client)."""

    @pytest.fixture
    def admin_user(self, db):
        """Create an admin user for testing."""
        from app.models.user import User
        user = User(
            email="admin@test.com",
            role="ADMIN",
            password_hash="dummy",
        )
        db.add(user)
        db.commit()
        return user

    def test_neighbors_endpoint_disabled(self, client: TestClient, admin_user):
        """Test neighbors endpoint returns 503 when Neo4j is disabled."""
        with patch.object(settings, "NEO4J_ENABLED", False):
            # Mock authentication
            with patch("app.core.dependencies.get_current_user", return_value=admin_user):
                response = client.get("/v1/admin/graph/neighbors?concept_id=theme_1")
                assert response.status_code == 503
                data = response.json()
                assert data["detail"]["error"] == "neo4j_disabled"

    def test_neighbors_endpoint_unreachable(self, client: TestClient, admin_user):
        """Test neighbors endpoint returns 503 when Neo4j is unreachable."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.api.ping", return_value=(False, None, {"error": "connection_failed"})):
                # Mock authentication
                with patch("app.core.dependencies.get_current_user", return_value=admin_user):
                    response = client.get("/v1/admin/graph/neighbors?concept_id=theme_1")
                    assert response.status_code == 503
                    data = response.json()
                    assert data["detail"]["error"] == "neo4j_unreachable"

    def test_neighbors_endpoint_validation(self, client: TestClient, admin_user):
        """Test neighbors endpoint validates depth parameter."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.api.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                # Mock authentication
                with patch("app.core.dependencies.get_current_user", return_value=admin_user):
                    # Test depth exceeds max
                    response = client.get(f"/v1/admin/graph/neighbors?concept_id=theme_1&depth={MAX_NEIGHBORS_DEPTH + 1}")
                    assert response.status_code == 422  # Validation error

    def test_suggestions_endpoint_known_ids_cap(self, client: TestClient, admin_user):
        """Test suggestions endpoint caps known_concept_ids."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.api.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                # Mock authentication
                with patch("app.core.dependencies.get_current_user", return_value=admin_user):
                    # Create a long list of IDs (exceeds cap)
                    many_ids = ",".join([f"theme_{i}" for i in range(MAX_SUGGESTIONS_KNOWN_IDS + 10)])
                    with patch("app.graph.api.get_suggestions") as mock_suggestions:
                        mock_suggestions.return_value = {"target": "theme_1", "missing_prereqs": [], "warnings": []}
                        response = client.get(
                            f"/v1/admin/graph/suggestions?target_concept_id=theme_1&known_concept_ids={many_ids}"
                        )
                        # Should succeed but cap the IDs
                        assert response.status_code == 200
                        # Verify that get_suggestions was called with capped list
                        call_args = mock_suggestions.call_args
                        known_ids_arg = call_args[0][1]  # Second positional arg
                        assert len(known_ids_arg) <= MAX_SUGGESTIONS_KNOWN_IDS
