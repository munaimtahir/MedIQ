"""Tests for search health endpoint."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.search.health import get_health_info


class TestSearchHealth:
    """Test search health functionality."""

    def test_get_health_info_disabled(self):
        """Test health info when Elasticsearch is disabled."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", False):
            with patch.object(settings, "ELASTICSEARCH_URL", "http://test:9200"):
                with patch.object(settings, "ELASTICSEARCH_INDEX_PREFIX", "test"):
                    health = get_health_info()
                    assert health["enabled"] is False
                    assert health["reachable"] is False
                    assert health["indices"] == []
                    assert health["aliases"] is None

    def test_get_health_info_enabled_but_unavailable(self):
        """Test health info when enabled but unavailable."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch.object(settings, "ELASTICSEARCH_URL", "http://test:9200"):
                with patch.object(settings, "ELASTICSEARCH_INDEX_PREFIX", "test"):
                    with patch("app.search.health.get_es_client", return_value=None):
                        health = get_health_info()
                        assert health["enabled"] is True
                        assert health["reachable"] is False
                        assert health["indices"] == []
                        assert health["aliases"] is None

    def test_get_health_info_enabled_and_available(self):
        """Test health info when enabled and available."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch.object(settings, "ELASTICSEARCH_URL", "http://test:9200"):
                with patch.object(settings, "ELASTICSEARCH_INDEX_PREFIX", "test"):
                    mock_client = MagicMock()
                    mock_client.cluster.health.return_value = {"status": "green"}
                    mock_client.indices.get.return_value = {
                        "test_index_1": {},
                        "test_index_2": {},
                    }
                    mock_client.indices.stats.return_value = {
                        "indices": {
                            "test_index_1": {"total": {"docs": {"count": 100}}},
                            "test_index_2": {"total": {"docs": {"count": 200}}},
                        }
                    }

                    with patch("app.search.health.get_es_client", return_value=mock_client):
                        health = get_health_info()
                        assert health["enabled"] is True
                        assert health["reachable"] is True
                        assert len(health["indices"]) == 2
                        assert health["indices"][0]["name"] == "test_index_1"
                        assert health["indices"][0]["doc_count"] == 100

    def test_get_health_info_handles_exceptions(self):
        """Test health info handles exceptions gracefully."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch.object(settings, "ELASTICSEARCH_URL", "http://test:9200"):
                with patch.object(settings, "ELASTICSEARCH_INDEX_PREFIX", "test"):
                    mock_client = MagicMock()
                    mock_client.cluster.health.side_effect = Exception("Connection error")

                    with patch("app.search.health.get_es_client", return_value=mock_client):
                        # Should not raise, should return safe response
                        health = get_health_info()
                        assert health["enabled"] is True
                        assert health["reachable"] is False
                        assert health["indices"] == []


class TestSearchHealthEndpoint:
    """Test search health endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def admin_user(self):
        """Create mock admin user."""
        from app.models.user import User

        user = MagicMock(spec=User)
        user.role = "ADMIN"
        user.id = "test-admin-id"
        return user

    def test_health_endpoint_requires_auth(self, client):
        """Test health endpoint requires authentication."""
        response = client.get("/v1/admin/search/health")
        assert response.status_code in (401, 403)

    def test_health_endpoint_disabled(self, client, admin_user):
        """Test health endpoint when Elasticsearch is disabled."""
        with patch("app.api.v1.endpoints.admin_search.get_current_user", return_value=admin_user):
            with patch.object(settings, "ELASTICSEARCH_ENABLED", False):
                with patch("app.api.v1.endpoints.admin_search.get_health_info") as mock_health:
                    mock_health.return_value = {
                        "enabled": False,
                        "reachable": False,
                        "url": "http://test:9200",
                        "index_prefix": "test",
                        "indices": [],
                        "aliases": None,
                        "last_sync_run": None,
                        "pending_outbox": None,
                    }
                    response = client.get("/v1/admin/search/health")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["enabled"] is False
                    assert data["reachable"] is False

    def test_health_endpoint_handles_exceptions(self, client, admin_user):
        """Test health endpoint handles exceptions gracefully."""
        with patch("app.api.v1.endpoints.admin_search.get_current_user", return_value=admin_user):
            with patch("app.api.v1.endpoints.admin_search.get_health_info") as mock_health:
                mock_health.side_effect = Exception("Unexpected error")
                response = client.get("/v1/admin/search/health")
                # Should not return 500, should return safe response
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is False
                assert data["reachable"] is False
