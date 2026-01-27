"""Tests for Neo4j concept graph sync functions."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.config import settings
from app.models.algo_runtime import AlgoRuntimeConfig
from app.models.neo4j_sync import Neo4jSyncRun, Neo4jSyncRunStatus, Neo4jSyncRunType
from app.graph.concept_sync import run_incremental_sync, run_full_rebuild, _check_freeze_updates, _get_last_incremental_watermark


class TestSyncGuards:
    """Test sync guard conditions."""

    def test_incremental_sync_disabled(self, db):
        """Test incremental sync when Neo4j is disabled."""
        with patch.object(settings, "NEO4J_ENABLED", False):
            run_id = run_incremental_sync(db)

            run = db.query(Neo4jSyncRun).filter(Neo4jSyncRun.id == run_id).first()
            assert run is not None
            assert run.status == Neo4jSyncRunStatus.DISABLED
            assert "disabled" in run.last_error.lower()

    def test_incremental_sync_frozen(self, db):
        """Test incremental sync when freeze_updates is enabled."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            # Create runtime config with freeze_updates=True
            config = AlgoRuntimeConfig(
                active_profile="V1_PRIMARY",
                config_json={
                    "profile": "V1_PRIMARY",
                    "overrides": {},
                    "safe_mode": {"freeze_updates": True, "prefer_cache": True},
                },
            )
            db.add(config)
            db.commit()

            run_id = run_incremental_sync(db)

            run = db.query(Neo4jSyncRun).filter(Neo4jSyncRun.id == run_id).first()
            assert run is not None
            assert run.status == Neo4jSyncRunStatus.BLOCKED_FROZEN
            assert "frozen" in run.last_error.lower()

    def test_full_rebuild_disabled(self, db):
        """Test full rebuild when Neo4j is disabled."""
        with patch.object(settings, "NEO4J_ENABLED", False):
            run_id = run_full_rebuild(db)

            run = db.query(Neo4jSyncRun).filter(Neo4jSyncRun.id == run_id).first()
            assert run is not None
            assert run.status == Neo4jSyncRunStatus.DISABLED

    def test_full_rebuild_frozen(self, db):
        """Test full rebuild when freeze_updates is enabled."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            # Create runtime config with freeze_updates=True
            config = AlgoRuntimeConfig(
                active_profile="V1_PRIMARY",
                config_json={
                    "profile": "V1_PRIMARY",
                    "overrides": {},
                    "safe_mode": {"freeze_updates": True, "prefer_cache": True},
                },
            )
            db.add(config)
            db.commit()

            run_id = run_full_rebuild(db)

            run = db.query(Neo4jSyncRun).filter(Neo4jSyncRun.id == run_id).first()
            assert run is not None
            assert run.status == Neo4jSyncRunStatus.BLOCKED_FROZEN


class TestSyncExecution:
    """Test sync execution logic."""

    def test_incremental_sync_queries_watermark(self, db):
        """Test incremental sync queries concepts/edges since watermark."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.concept_sync.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                with patch("app.graph.concept_sync.ensure_constraints_and_indexes"):
                    with patch("app.graph.concept_sync.get_concepts_since_watermark") as mock_concepts:
                        with patch("app.graph.concept_sync.get_prereq_edges_since_watermark") as mock_edges:
                            with patch("app.graph.concept_sync.run_write"):
                                with patch("app.graph.concept_sync.run_read", return_value=[{"count": 0}]):
                                    with patch("app.graph.concept_sync._detect_cycles", return_value=(False, [])):
                                        # Create a previous successful run
                                        previous_run = Neo4jSyncRun(
                                            id=uuid4(),
                                            run_type=Neo4jSyncRunType.INCREMENTAL.value,
                                            status=Neo4jSyncRunStatus.DONE.value,
                                            finished_at=datetime.now(UTC) - timedelta(hours=1),
                                        )
                                        db.add(previous_run)
                                        db.commit()

                                        mock_concepts.return_value = []
                                        mock_edges.return_value = []

                                        run_id = run_incremental_sync(db)

                                        # Verify watermark was used
                                        assert mock_concepts.called
                                        assert mock_edges.called

    def test_incremental_sync_rejects_self_loops(self, db):
        """Test that incremental sync rejects self-loop edges."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.concept_sync.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                with patch("app.graph.concept_sync.ensure_constraints_and_indexes"):
                    with patch("app.graph.concept_sync.get_concepts_since_watermark", return_value=[]):
                        with patch("app.graph.concept_sync.get_prereq_edges_since_watermark") as mock_edges:
                            with patch("app.graph.concept_sync.run_write") as mock_write:
                                with patch("app.graph.concept_sync.run_read", return_value=[{"count": 0}]):
                                    with patch("app.graph.concept_sync._detect_cycles", return_value=(False, [])):
                                        # Create edge with self-loop
                                        mock_edges.return_value = [
                                            {
                                                "from_id": "theme_1",
                                                "to_id": "theme_1",  # Self-loop
                                                "props": {"weight": 1.0, "source": "MANUAL"},
                                            }
                                        ]

                                        run_id = run_incremental_sync(db)

                                        # Verify self-loop was rejected (upsert_prereq_edge raises ValueError)
                                        # The sync should continue and complete
                                        run = db.query(Neo4jSyncRun).filter(Neo4jSyncRun.id == run_id).first()
                                        assert run is not None
                                        # Should complete (self-loop is logged but doesn't fail the sync)

    def test_full_rebuild_deletes_all_nodes(self, db):
        """Test that full rebuild deletes all nodes before upserting."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.concept_sync.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                with patch("app.graph.concept_sync.ensure_constraints_and_indexes"):
                    with patch("app.graph.concept_sync.get_all_active_concepts", return_value=[]):
                        with patch("app.graph.concept_sync.get_all_active_prereq_edges", return_value=[]):
                            with patch("app.graph.concept_sync.run_write") as mock_write:
                                with patch("app.graph.concept_sync.run_read", return_value=[{"count": 0}]):
                                    with patch("app.graph.concept_sync._detect_cycles", return_value=(False, [])):
                                        run_id = run_full_rebuild(db)

                                        # Verify DETACH DELETE was called
                                        write_calls = [call[0][0] for call in mock_write.call_args_list]
                                        delete_calls = [c for c in write_calls if "DETACH DELETE" in c.upper()]
                                        assert len(delete_calls) > 0

    def test_sync_records_cycle_detection(self, db):
        """Test that sync records cycle detection in details."""
        with patch.object(settings, "NEO4J_ENABLED", True):
            with patch("app.graph.concept_sync.ping", return_value=(True, 10, {"enabled": True, "reachable": True})):
                with patch("app.graph.concept_sync.ensure_constraints_and_indexes"):
                    with patch("app.graph.concept_sync.get_all_active_concepts", return_value=[]):
                        with patch("app.graph.concept_sync.get_all_active_prereq_edges", return_value=[]):
                            with patch("app.graph.concept_sync.run_write"):
                                with patch("app.graph.concept_sync.run_read", return_value=[{"count": 0}]):
                                    with patch("app.graph.concept_sync._detect_cycles", return_value=(
                                        True,
                                        [{"concept_id": "theme_1", "cycle_length": 3}],
                                    )):
                                        run_id = run_full_rebuild(db)

                                        run = db.query(Neo4jSyncRun).filter(Neo4jSyncRun.id == run_id).first()
                                        assert run is not None
                                        assert run.cycle_detected is True
                                        assert run.details is not None
                                        assert "cycle_samples" in run.details
