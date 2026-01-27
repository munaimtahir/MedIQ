"""Tests for student graph exploration endpoints."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.algo_runtime import AlgoRuntimeConfig, AlgoRuntimeProfile


class TestStudentGraphFeatureFlag:
    """Test feature flag enforcement."""

    def test_endpoints_return_404_when_feature_disabled(self, client: TestClient, auth_headers_student, db):
        """Test that endpoints return 404 when feature flag is disabled."""
        with patch.object(settings, "FEATURE_STUDENT_CONCEPT_EXPLORER", False):
            response = client.get("/v1/student/graph/neighbors?concept_id=theme_1", headers=auth_headers_student)
            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["error"] == "feature_disabled"

    def test_endpoints_work_when_feature_enabled(self, client: TestClient, auth_headers_student, db):
        """Test that endpoints work when feature flag is enabled."""
        # Create runtime config with graph_mode=shadow
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"graph_mode": "shadow"},
        )
        db.add(config)
        db.commit()

        with patch.object(settings, "FEATURE_STUDENT_CONCEPT_EXPLORER", True):
            with patch.object(settings, "NEO4J_ENABLED", True):
                with patch("app.graph.readiness.evaluate_graph_readiness") as mock_readiness:
                    from app.graph.readiness import GraphReadiness, ReadinessCheckResult
                    mock_readiness.return_value = GraphReadiness(
                        ready=True,
                        checks={},
                        blocking_reasons=[],
                    )
                    with patch("app.graph.service.get_neighbors", return_value={
                        "concept_id": "theme_1",
                        "depth": 1,
                        "prereqs": [],
                        "dependents": [],
                        "warnings": [],
                    }):
                        response = client.get("/v1/student/graph/neighbors?concept_id=theme_1", headers=auth_headers_student)
                        assert response.status_code == 200


class TestStudentGraphLimits:
    """Test student-specific hard caps."""

    def test_neighbors_depth_capped_at_1(self, client: TestClient, auth_headers_student):
        """Test that neighbors depth is capped at 1 for students."""
        with patch.object(settings, "FEATURE_STUDENT_CONCEPT_EXPLORER", True):
            # Try depth=2 (should be rejected by validation)
            response = client.get("/v1/student/graph/neighbors?concept_id=theme_1&depth=2", headers=auth_headers_student)
            assert response.status_code == 422  # Validation error

    def test_prereqs_max_depth_capped_at_4(self, client: TestClient, auth_headers_student):
        """Test that prerequisites max_depth is capped at 4 for students."""
        with patch.object(settings, "FEATURE_STUDENT_CONCEPT_EXPLORER", True):
            # Try max_depth=5 (should be rejected by validation)
            response = client.get("/v1/student/graph/prerequisites?concept_id=theme_1&max_depth=5", headers=auth_headers_student)
            assert response.status_code == 422  # Validation error

    def test_suggestions_limit_capped_at_10(self, client: TestClient, auth_headers_student):
        """Test that suggestions limit is capped at 10 for students."""
        with patch.object(settings, "FEATURE_STUDENT_CONCEPT_EXPLORER", True):
            # Try limit=11 (should be rejected by validation)
            response = client.get("/v1/student/graph/suggestions?target_concept_id=theme_1&limit=11", headers=auth_headers_student)
            assert response.status_code == 422  # Validation error


class TestStudentGraphUnavailable:
    """Test graph unavailable handling."""

    def test_returns_503_when_graph_disabled(self, client: TestClient, auth_headers_student, db):
        """Test that endpoints return 503 when graph is disabled."""
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"graph_mode": "disabled"},
        )
        db.add(config)
        db.commit()

        with patch.object(settings, "FEATURE_STUDENT_CONCEPT_EXPLORER", True):
            response = client.get("/v1/student/graph/neighbors?concept_id=theme_1", headers=auth_headers_student)
            assert response.status_code == 503
            data = response.json()
            assert data["detail"]["error"] == "graph_unavailable"

    def test_returns_503_when_graph_not_ready(self, client: TestClient, auth_headers_student, db):
        """Test that endpoints return 503 when graph is not ready."""
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"graph_mode": "shadow"},
        )
        db.add(config)
        db.commit()

        with patch.object(settings, "FEATURE_STUDENT_CONCEPT_EXPLORER", True):
            with patch.object(settings, "NEO4J_ENABLED", True):
                with patch("app.graph.readiness.evaluate_graph_readiness") as mock_readiness:
                    from app.graph.readiness import GraphReadiness, ReadinessCheckResult
                    mock_readiness.return_value = GraphReadiness(
                        ready=False,
                        checks={"env_enabled": ReadinessCheckResult(ok=False)},
                        blocking_reasons=["Neo4j not enabled"],
                    )
                    response = client.get("/v1/student/graph/neighbors?concept_id=theme_1", headers=auth_headers_student)
                    assert response.status_code == 503
                    data = response.json()
                    assert data["detail"]["error"] == "graph_unavailable"
