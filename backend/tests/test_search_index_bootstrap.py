"""Tests for search index bootstrap."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC

from app.core.config import settings
from app.search.index_bootstrap import (
    build_questions_v1_mapping,
    build_questions_v1_settings,
    generate_questions_index_name,
    create_questions_index,
    get_current_questions_index,
    swap_questions_aliases,
    ensure_questions_aliases_exist,
    get_questions_read_alias,
    get_questions_write_alias,
)


class TestIndexBootstrap:
    """Test index bootstrap functionality."""

    def test_build_questions_v1_mapping(self):
        """Test mapping builder returns valid structure."""
        mapping = build_questions_v1_mapping()

        assert "properties" in mapping
        props = mapping["properties"]

        # Check required fields
        assert "question_id" in props
        assert props["question_id"]["type"] == "keyword"

        assert "stem" in props
        assert props["stem"]["type"] == "text"
        assert props["stem"]["analyzer"] == "english"

        assert "theme_name" in props
        assert props["theme_name"]["type"] == "text"
        assert "fields" in props["theme_name"]
        assert "keyword" in props["theme_name"]["fields"]

        assert "year" in props
        assert props["year"]["type"] == "integer"

    def test_build_questions_v1_settings(self):
        """Test settings builder returns valid structure."""
        settings_dict = build_questions_v1_settings()

        assert "number_of_shards" in settings_dict
        assert "number_of_replicas" in settings_dict
        assert "analysis" in settings_dict
        assert settings_dict["number_of_shards"] == 1
        assert settings_dict["number_of_replicas"] == 0

    def test_generate_questions_index_name(self):
        """Test index name generation includes prefix and version."""
        timestamp = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)
        index_name = generate_questions_index_name(timestamp)

        assert index_name.startswith(settings.ELASTICSEARCH_INDEX_PREFIX)
        assert "_questions_v1_" in index_name
        assert "20260123T120000Z" in index_name

    def test_get_questions_aliases_include_prefix(self):
        """Test alias names include prefix."""
        read_alias = get_questions_read_alias()
        write_alias = get_questions_write_alias()

        assert read_alias.startswith(settings.ELASTICSEARCH_INDEX_PREFIX)
        assert write_alias.startswith(settings.ELASTICSEARCH_INDEX_PREFIX)
        assert read_alias.endswith("_questions_read")
        assert write_alias.endswith("_questions_write")

    def test_ensure_questions_aliases_exist_disabled(self):
        """Test bootstrap no-op when ES disabled."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", False):
            result = ensure_questions_aliases_exist()
            assert result["created"] is False
            assert result["index_name"] is None

    def test_ensure_questions_aliases_exist_creates_index(self):
        """Test bootstrap creates index when aliases don't exist."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            mock_client = MagicMock()
            mock_client.indices.get_alias.return_value = {}  # No existing aliases
            mock_client.indices.create.return_value = {"acknowledged": True}
            mock_client.indices.update_aliases.return_value = {"acknowledged": True}

            with patch("app.search.index_bootstrap.get_es_client", return_value=mock_client):
                result = ensure_questions_aliases_exist()
                assert result["created"] is True
                assert result["index_name"] is not None
                mock_client.indices.create.assert_called_once()
                mock_client.indices.update_aliases.assert_called_once()

    def test_ensure_questions_aliases_exist_uses_existing(self):
        """Test bootstrap uses existing index if aliases exist."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            mock_client = MagicMock()
            existing_index = f"{settings.ELASTICSEARCH_INDEX_PREFIX}_questions_v1_20260123T120000Z"
            mock_client.indices.get_alias.return_value = {
                existing_index: {"aliases": {get_questions_write_alias(): {}}}
            }

            with patch("app.search.index_bootstrap.get_es_client", return_value=mock_client):
                with patch(
                    "app.search.index_bootstrap.get_current_questions_index",
                    return_value=existing_index,
                ):
                    result = ensure_questions_aliases_exist()
                    assert result["created"] is False
                    assert result["index_name"] == existing_index
                    mock_client.indices.create.assert_not_called()

    def test_get_current_questions_index(self):
        """Test getting current index from alias."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            mock_client = MagicMock()
            existing_index = f"{settings.ELASTICSEARCH_INDEX_PREFIX}_questions_v1_20260123T120000Z"
            mock_client.indices.get_alias.return_value = {
                existing_index: {"aliases": {get_questions_write_alias(): {}}}
            }

            with patch("app.search.index_bootstrap.get_es_client", return_value=mock_client):
                index_name = get_current_questions_index()
                assert index_name == existing_index

    def test_get_current_questions_index_none_when_disabled(self):
        """Test returns None when ES disabled."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", False):
            index_name = get_current_questions_index()
            assert index_name is None

    def test_swap_questions_aliases(self):
        """Test alias swap operation."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            mock_client = MagicMock()
            old_index = f"{settings.ELASTICSEARCH_INDEX_PREFIX}_questions_v1_20260123T120000Z"
            new_index = f"{settings.ELASTICSEARCH_INDEX_PREFIX}_questions_v1_20260124T120000Z"

            with patch("app.search.index_bootstrap.get_es_client", return_value=mock_client):
                with patch(
                    "app.search.index_bootstrap.get_current_questions_index",
                    return_value=old_index,
                ):
                    swap_questions_aliases(new_index)

                    # Verify update_aliases was called with correct actions
                    mock_client.indices.update_aliases.assert_called_once()
                    call_args = mock_client.indices.update_aliases.call_args
                    actions = call_args[1]["body"]["actions"]

                    # Should have 4 actions: 2 removes, 2 adds
                    assert len(actions) == 4
                    assert any(
                        action.get("remove", {}).get("index") == old_index for action in actions
                    )
                    assert any(
                        action.get("add", {}).get("index") == new_index for action in actions
                    )
