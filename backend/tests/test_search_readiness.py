"""Tests for Elasticsearch readiness evaluation."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.config import settings
from app.models.algo_runtime import AlgoRuntimeConfig
from app.models.question_cms import Question, QuestionStatus
from app.models.search_indexing import SearchSyncRun, SearchSyncRunStatus, SearchSyncRunType
from app.search.readiness import (
    evaluate_elasticsearch_readiness,
    _check_service_health,
    _check_reachability,
    _check_alias_exists,
    _check_index_health,
    _check_doc_count,
    _check_sync_freshness,
    _check_error_budget,
)


class TestReadinessChecks:
    """Test individual readiness checks."""

    def test_check_service_health_enabled(self):
        """Test service health check when enabled."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            result = _check_service_health()
            assert result.ok is True
            assert result.details["enabled"] is True

    def test_check_service_health_disabled(self):
        """Test service health check when disabled."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", False):
            result = _check_service_health()
            assert result.ok is False
            assert result.details["enabled"] is False

    def test_check_reachability_success(self):
        """Test reachability check when ES is reachable."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.readiness.ping", return_value=True):
                result = _check_reachability()
                assert result.ok is True
                assert result.details["reachable"] is True
                assert "latency_ms" in result.details

    def test_check_reachability_failure(self):
        """Test reachability check when ES is unreachable."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.readiness.ping", return_value=False):
                result = _check_reachability()
                assert result.ok is False
                assert result.details["reachable"] is False

    def test_check_alias_exists_success(self, db):
        """Test alias check when alias exists."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.readiness.get_es_client") as mock_client:
                mock_es = MagicMock()
                mock_client.return_value = mock_es
                mock_es.indices.get_alias.return_value = {"test_index": {}}

                with patch("app.search.readiness.get_questions_read_alias", return_value="test_alias"):
                    with patch("app.search.readiness.get_current_questions_index", return_value="test_index"):
                        result = _check_alias_exists()
                        assert result.ok is True
                        assert result.details["alias"] == "test_alias"
                        assert result.details["index"] == "test_index"

    def test_check_alias_exists_missing(self, db):
        """Test alias check when alias doesn't exist."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.readiness.get_es_client") as mock_client:
                mock_es = MagicMock()
                mock_client.return_value = mock_es

                with patch("app.search.readiness.get_current_questions_index", return_value=None):
                    result = _check_alias_exists()
                    assert result.ok is False
                    assert result.details["index"] is None

    def test_check_index_health_green(self, db):
        """Test index health check when status is green."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.readiness.get_es_client") as mock_client:
                mock_es = MagicMock()
                mock_client.return_value = mock_es
                mock_es.cluster.health.return_value = {
                    "status": "green",
                    "indices": {
                        "test_index": {
                            "status": "green",
                        }
                    },
                }

                with patch("app.search.readiness.get_current_questions_index", return_value="test_index"):
                    result = _check_index_health()
                    assert result.ok is True
                    assert result.details["status"] == "green"

    def test_check_index_health_red(self, db):
        """Test index health check when status is red."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.readiness.get_es_client") as mock_client:
                mock_es = MagicMock()
                mock_client.return_value = mock_es
                mock_es.cluster.health.return_value = {
                    "status": "red",
                    "indices": {
                        "test_index": {
                            "status": "red",
                        }
                    },
                }

                with patch("app.search.readiness.get_current_questions_index", return_value="test_index"):
                    result = _check_index_health()
                    assert result.ok is False
                    assert result.details["status"] == "red"

    def test_check_doc_count_sufficient(self, db):
        """Test doc count check when count is sufficient."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch.object(settings, "ELASTICSEARCH_MIN_PUBLISHED_QUESTIONS", 500):
                with patch("app.search.readiness.get_es_client") as mock_client:
                    mock_es = MagicMock()
                    mock_client.return_value = mock_es
                    mock_es.indices.stats.return_value = {
                        "indices": {
                            "test_index": {
                                "total": {
                                    "docs": {
                                        "count": 1000,
                                    }
                                }
                            }
                        }
                    }

                    with patch("app.search.readiness.get_current_questions_index", return_value="test_index"):
                        # Create some published questions in DB
                        for i in range(1000):
                            question = Question(
                                id=uuid4(),
                                stem=f"Question {i}",
                                status=QuestionStatus.PUBLISHED,
                            )
                            db.add(question)
                        db.commit()

                        result = _check_doc_count(db)
                        assert result.ok is True
                        assert result.details["count"] == 1000

    def test_check_doc_count_insufficient(self, db):
        """Test doc count check when count is insufficient."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch.object(settings, "ELASTICSEARCH_MIN_PUBLISHED_QUESTIONS", 500):
                with patch("app.search.readiness.get_es_client") as mock_client:
                    mock_es = MagicMock()
                    mock_client.return_value = mock_es
                    mock_es.indices.stats.return_value = {
                        "indices": {
                            "test_index": {
                                "total": {
                                    "docs": {
                                        "count": 100,  # Below threshold
                                    }
                                }
                            }
                        }
                    }

                    with patch("app.search.readiness.get_current_questions_index", return_value="test_index"):
                        result = _check_doc_count(db)
                        assert result.ok is False
                        assert result.details["count"] == 100
                        assert result.details["expected_min"] == 500

    def test_check_sync_freshness_recent(self, db):
        """Test sync freshness check when last sync is recent."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch.object(settings, "ELASTICSEARCH_SYNC_FRESHNESS_HOURS", 24):
                # Create a recent successful nightly run
                recent_run = SearchSyncRun(
                    id=uuid4(),
                    run_type=SearchSyncRunType.NIGHTLY,
                    status=SearchSyncRunStatus.DONE,
                    finished_at=datetime.now(UTC) - timedelta(hours=1),  # 1 hour ago
                    indexed_count=1000,
                )
                db.add(recent_run)
                db.commit()

                result = _check_sync_freshness(db)
                assert result.ok is True
                assert "last_run_at" in result.details

    def test_check_sync_freshness_stale(self, db):
        """Test sync freshness check when last sync is stale."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch.object(settings, "ELASTICSEARCH_SYNC_FRESHNESS_HOURS", 24):
                # Create a stale successful nightly run
                stale_run = SearchSyncRun(
                    id=uuid4(),
                    run_type=SearchSyncRunType.NIGHTLY,
                    status=SearchSyncRunStatus.DONE,
                    finished_at=datetime.now(UTC) - timedelta(hours=48),  # 48 hours ago
                    indexed_count=1000,
                )
                db.add(stale_run)
                db.commit()

                result = _check_sync_freshness(db)
                assert result.ok is False

    def test_check_error_budget_no_failures(self, db):
        """Test error budget check when no recent failures."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch.object(settings, "ELASTICSEARCH_ERROR_BUDGET_RUNS", 3):
                # Create successful runs
                for i in range(3):
                    run = SearchSyncRun(
                        id=uuid4(),
                        run_type=SearchSyncRunType.NIGHTLY,
                        status=SearchSyncRunStatus.DONE,
                        finished_at=datetime.now(UTC) - timedelta(hours=i),
                        indexed_count=1000,
                    )
                    db.add(run)
                db.commit()

                result = _check_error_budget(db)
                assert result.ok is True
                assert result.details["recent_failures"] == 0

    def test_check_error_budget_has_failures(self, db):
        """Test error budget check when recent failures exist."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch.object(settings, "ELASTICSEARCH_ERROR_BUDGET_RUNS", 3):
                # Create runs with failures
                for i in range(3):
                    run = SearchSyncRun(
                        id=uuid4(),
                        run_type=SearchSyncRunType.NIGHTLY,
                        status=SearchSyncRunStatus.FAILED if i == 0 else SearchSyncRunStatus.DONE,
                        finished_at=datetime.now(UTC) - timedelta(hours=i),
                        indexed_count=1000,
                    )
                    db.add(run)
                db.commit()

                result = _check_error_budget(db)
                assert result.ok is False
                assert result.details["recent_failures"] == 1


class TestReadinessEvaluation:
    """Test full readiness evaluation."""

    def test_readiness_all_checks_pass(self, db):
        """Test readiness when all checks pass."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.readiness.ping", return_value=True):
                with patch("app.search.readiness.get_es_client") as mock_client:
                    mock_es = MagicMock()
                    mock_client.return_value = mock_es
                    mock_es.indices.get_alias.return_value = {"test_index": {}}
                    mock_es.cluster.health.return_value = {
                        "status": "green",
                        "indices": {
                            "test_index": {
                                "status": "green",
                            }
                        },
                    }
                    mock_es.indices.stats.return_value = {
                        "indices": {
                            "test_index": {
                                "total": {
                                    "docs": {
                                        "count": 1000,
                                    }
                                }
                            }
                        }
                    }

                    with patch("app.search.readiness.get_questions_read_alias", return_value="test_alias"):
                        with patch("app.search.readiness.get_current_questions_index", return_value="test_index"):
                            # Create published questions
                            for i in range(1000):
                                question = Question(
                                    id=uuid4(),
                                    stem=f"Question {i}",
                                    status=QuestionStatus.PUBLISHED,
                                )
                                db.add(question)

                            # Create recent successful sync
                            recent_run = SearchSyncRun(
                                id=uuid4(),
                                run_type=SearchSyncRunType.NIGHTLY,
                                status=SearchSyncRunStatus.DONE,
                                finished_at=datetime.now(UTC) - timedelta(hours=1),
                                indexed_count=1000,
                            )
                            db.add(recent_run)
                            db.commit()

                            result = evaluate_elasticsearch_readiness(db)
                            assert result.ready is True
                            assert len(result.blocking_reasons) == 0

    def test_readiness_alias_missing(self, db):
        """Test readiness when alias is missing."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch("app.search.readiness.ping", return_value=True):
                with patch("app.search.readiness.get_current_questions_index", return_value=None):
                    result = evaluate_elasticsearch_readiness(db)
                    assert result.ready is False
                    assert any("alias" in reason.lower() for reason in result.blocking_reasons)

    def test_readiness_doc_count_below_threshold(self, db):
        """Test readiness when doc count is below threshold."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch.object(settings, "ELASTICSEARCH_MIN_PUBLISHED_QUESTIONS", 500):
                with patch("app.search.readiness.ping", return_value=True):
                    with patch("app.search.readiness.get_es_client") as mock_client:
                        mock_es = MagicMock()
                        mock_client.return_value = mock_es
                        mock_es.indices.get_alias.return_value = {"test_index": {}}
                        mock_es.cluster.health.return_value = {
                            "status": "green",
                            "indices": {
                                "test_index": {
                                    "status": "green",
                                }
                            },
                        }
                        mock_es.indices.stats.return_value = {
                            "indices": {
                                "test_index": {
                                    "total": {
                                        "docs": {
                                            "count": 100,  # Below threshold
                                        }
                                    }
                                }
                            }
                        }

                        with patch("app.search.readiness.get_questions_read_alias", return_value="test_alias"):
                            with patch("app.search.readiness.get_current_questions_index", return_value="test_index"):
                                result = evaluate_elasticsearch_readiness(db)
                                assert result.ready is False
                                assert any("Insufficient documents" in reason for reason in result.blocking_reasons)

    def test_readiness_sync_stale(self, db):
        """Test readiness when last sync is stale."""
        with patch.object(settings, "ELASTICSEARCH_ENABLED", True):
            with patch.object(settings, "ELASTICSEARCH_SYNC_FRESHNESS_HOURS", 24):
                with patch("app.search.readiness.ping", return_value=True):
                    with patch("app.search.readiness.get_es_client") as mock_client:
                        mock_es = MagicMock()
                        mock_client.return_value = mock_es
                        mock_es.indices.get_alias.return_value = {"test_index": {}}
                        mock_es.cluster.health.return_value = {
                            "status": "green",
                            "indices": {
                                "test_index": {
                                    "status": "green",
                                }
                            },
                        }
                        mock_es.indices.stats.return_value = {
                            "indices": {
                                "test_index": {
                                    "total": {
                                        "docs": {
                                            "count": 1000,
                                        }
                                    }
                                }
                            }
                        }

                        with patch("app.search.readiness.get_questions_read_alias", return_value="test_alias"):
                            with patch("app.search.readiness.get_current_questions_index", return_value="test_index"):
                                # Create stale sync
                                stale_run = SearchSyncRun(
                                    id=uuid4(),
                                    run_type=SearchSyncRunType.NIGHTLY,
                                    status=SearchSyncRunStatus.DONE,
                                    finished_at=datetime.now(UTC) - timedelta(hours=48),
                                    indexed_count=1000,
                                )
                                db.add(stale_run)
                                db.commit()

                                result = evaluate_elasticsearch_readiness(db)
                                assert result.ready is False
                                assert any("sync" in reason.lower() for reason in result.blocking_reasons)
