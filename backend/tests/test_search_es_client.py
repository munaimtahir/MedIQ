"""Tests for Elasticsearch client."""

import pytest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.search.es_client import get_es_client, ping, reset_client


class TestESClient:
    """Test Elasticsearch client functionality."""

    def setup_method(self):
        """Reset client before each test."""
        reset_client()

    def test_get_es_client_disabled(self):
        """Test that client returns None when disabled."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", False):
            client = get_es_client()
            assert client is None

    def test_get_es_client_enabled_but_unavailable(self):
        """Test that client returns None when enabled but unavailable."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.es_client.Elasticsearch") as mock_es:
                mock_client = MagicMock()
                mock_es.return_value = mock_client
                mock_client.ping.return_value = False

                client = get_es_client()
                assert client is None

    def test_get_es_client_enabled_and_available(self):
        """Test that client returns client when enabled and available."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.es_client.Elasticsearch") as mock_es:
                mock_client = MagicMock()
                mock_es.return_value = mock_client
                mock_client.ping.return_value = True

                client = get_es_client()
                assert client is not None
                assert client == mock_client

    def test_ping_disabled(self):
        """Test ping returns False when disabled."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", False):
            assert ping() is False

    def test_ping_enabled_but_fails(self):
        """Test ping returns False when enabled but connection fails."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.es_client.get_es_client", return_value=None):
                assert ping() is False

    def test_ping_enabled_and_succeeds(self):
        """Test ping returns True when enabled and connection succeeds."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            with patch("app.search.es_client.get_es_client", return_value=mock_client):
                assert ping() is True

    def test_ping_handles_exceptions(self):
        """Test ping handles exceptions gracefully."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Connection error")
            with patch("app.search.es_client.get_es_client", return_value=mock_client):
                # Should not raise, should return False
                assert ping() is False
