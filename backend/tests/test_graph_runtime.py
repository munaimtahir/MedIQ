"""Tests for Neo4j graph runtime endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.algo_runtime import AlgoRuntimeConfig, AlgoRuntimeProfile


class TestGraphRuntime:
    """Test graph runtime endpoints."""

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

    def test_get_runtime_defaults_to_disabled(self, client: TestClient, admin_user, db):
        """Test that graph runtime defaults to disabled."""
        # Create default runtime config without graph_mode
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={
                "profile": "V1_PRIMARY",
                "overrides": {},
                "safe_mode": {"freeze_updates": False},
            },
        )
        db.add(config)
        db.commit()

        with patch("app.core.dependencies.get_current_user", return_value=admin_user):
            with patch.object(settings, "NEO4J_ENABLED", False):
                response = client.get("/v1/admin/graph/runtime")
                assert response.status_code == 200
                data = response.json()
                assert data["requested_mode"] == "disabled"
                assert data["effective_mode"] == "disabled"

    def test_switch_requires_confirmation_phrase(self, client: TestClient, admin_user, db):
        """Test that switching requires correct confirmation phrase."""
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"graph_mode": "disabled"},
        )
        db.add(config)
        db.commit()

        with patch("app.core.dependencies.get_current_user", return_value=admin_user):
            # Wrong phrase
            response = client.post(
                "/v1/admin/graph/runtime/switch",
                json={
                    "mode": "shadow",
                    "reason": "Testing shadow mode",
                    "confirmation_phrase": "WRONG PHRASE",
                },
            )
            assert response.status_code == 400

            # Correct phrase
            response = client.post(
                "/v1/admin/graph/runtime/switch",
                json={
                    "mode": "shadow",
                    "reason": "Testing shadow mode activation",
                    "confirmation_phrase": "SWITCH GRAPH TO SHADOW",
                },
            )
            assert response.status_code == 200

    def test_switch_requires_reason(self, client: TestClient, admin_user, db):
        """Test that switching requires a reason."""
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"graph_mode": "disabled"},
        )
        db.add(config)
        db.commit()

        with patch("app.core.dependencies.get_current_user", return_value=admin_user):
            # Short reason
            response = client.post(
                "/v1/admin/graph/runtime/switch",
                json={
                    "mode": "shadow",
                    "reason": "short",
                    "confirmation_phrase": "SWITCH GRAPH TO SHADOW",
                },
            )
            assert response.status_code == 400

            # No reason
            response = client.post(
                "/v1/admin/graph/runtime/switch",
                json={
                    "mode": "shadow",
                    "reason": "",
                    "confirmation_phrase": "SWITCH GRAPH TO SHADOW",
                },
            )
            assert response.status_code == 400

    def test_effective_mode_downgrades_on_readiness_failure(self, client: TestClient, admin_user, db):
        """Test that effective mode downgrades when readiness fails."""
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"graph_mode": "shadow"},
        )
        db.add(config)
        db.commit()

        with patch("app.core.dependencies.get_current_user", return_value=admin_user):
            with patch.object(settings, "NEO4J_ENABLED", True):
                with patch("app.graph.readiness.evaluate_graph_readiness") as mock_readiness:
                    # Mock readiness failure
                    from app.graph.readiness import GraphReadiness, ReadinessCheckResult
                    mock_readiness.return_value = GraphReadiness(
                        ready=False,
                        checks={"env_enabled": ReadinessCheckResult(ok=False)},
                        blocking_reasons=["Neo4j not enabled in environment"],
                    )

                    response = client.get("/v1/admin/graph/runtime")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["requested_mode"] == "shadow"
                    assert data["effective_mode"] == "disabled"  # Downgraded

    def test_active_mode_requires_feature_flag(self, client: TestClient, admin_user, db):
        """Test that active mode requires FEATURE_GRAPH_ACTIVE flag."""
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"graph_mode": "disabled"},
        )
        db.add(config)
        db.commit()

        with patch("app.core.dependencies.get_current_user", return_value=admin_user):
            with patch.object(settings, "FEATURE_GRAPH_ACTIVE", False):
                response = client.post(
                    "/v1/admin/graph/runtime/switch",
                    json={
                        "mode": "active",
                        "reason": "Testing active mode activation",
                        "confirmation_phrase": "SWITCH GRAPH TO ACTIVE",
                    },
                )
                assert response.status_code == 400
                assert "FEATURE_GRAPH_ACTIVE" in response.json()["detail"]
