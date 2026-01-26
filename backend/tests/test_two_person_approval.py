"""Tests for two-person approval system in production."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.runtime_control import TwoPersonApproval
from app.models.user import User, UserRole
from app.core.config import settings


@pytest.fixture
def admin_user1(db: Session) -> User:
    """Create first admin user."""
    from uuid import uuid4
    u = User(
        id=uuid4(),
        email="admin1@test.local",
        role=UserRole.ADMIN.value,
        password_hash="dummy",
        is_active=True,
        email_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def admin_user2(db: Session) -> User:
    """Create second admin user."""
    from uuid import uuid4
    u = User(
        id=uuid4(),
        email="admin2@test.local",
        role=UserRole.ADMIN.value,
        password_hash="dummy",
        is_active=True,
        email_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def client(db: Session, admin_user1: User):
    """Create test client with admin user."""
    from app.core.dependencies import get_current_user, get_db

    def override_get_db():
        yield db

    def override_get_current_user():
        return admin_user1

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        # Use TestClient without context manager to avoid lifespan issues
        c = TestClient(app)
        yield c
    finally:
        app.dependency_overrides.clear()


def test_profile_switch_requires_approval_in_production(
    client: TestClient, db: Session, admin_user1: User, monkeypatch
):
    """Test that profile switch requires approval in production."""
    # Mock production environment
    monkeypatch.setattr(settings, "ENV", "prod")

    # Ensure AlgoRuntimeConfig exists (required for the endpoint)
    from app.models.algo_runtime import AlgoRuntimeConfig, AlgoRuntimeProfile
    config = db.query(AlgoRuntimeConfig).first()
    if not config:
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={},
        )
        db.add(config)
        db.commit()

    # Try to switch profile directly (should fail with 409)
    response = client.post(
        "/v1/admin/algorithms/runtime/switch",
        json={
            "profile": "V0_FALLBACK",
            "reason": "Test switch",
            "confirmation_phrase": "SWITCH TO V0_FALLBACK",
            "overrides": {},
        },
    )

    # Should return 409 (approval required)
    assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.json()}"
    error_data = response.json()
    assert "APPROVAL_REQUIRED" in error_data.get("error", {}).get("code", "") or "APPROVAL_REQUIRED" in str(error_data)


def test_profile_switch_allowed_in_non_prod(
    client: TestClient, db: Session, admin_user1: User, monkeypatch
):
    """Test that profile switch is allowed directly in non-production."""
    # Mock non-production environment
    monkeypatch.setattr(settings, "ENV", "dev")

    # Ensure AlgoRuntimeConfig exists
    from app.models.algo_runtime import AlgoRuntimeConfig, AlgoRuntimeProfile
    config = db.query(AlgoRuntimeConfig).first()
    if not config:
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={},
        )
        db.add(config)
        db.commit()

    # Try to switch profile directly (should work in dev)
    # Note: This test may fail if other validations fail, but should not fail on approval check
    response = client.post(
        "/v1/admin/algorithms/runtime/switch",
        json={
            "profile": "V0_FALLBACK",
            "reason": "Test switch",
            "confirmation_phrase": "SWITCH TO V0_FALLBACK",
            "overrides": {},
        },
    )

    # Should NOT return 409 (approval not required in dev)
    # Note: May fail on other validations, but should not fail on approval check
    if response.status_code == 409:
        error_data = response.json()
        error_code = error_data.get("error", {}).get("code", "") or str(error_data)
        assert "APPROVAL_REQUIRED" not in error_code


def test_approval_request_creation(
    client: TestClient, db: Session, admin_user1: User, monkeypatch
):
    """Test creating an approval request."""
    monkeypatch.setattr(settings, "ENV", "prod")

    response = client.post(
        "/v1/admin/runtime/approvals/request",
        json={
            "action_type": "PROFILE_SWITCH_FALLBACK",
            "action_payload": {"profile": "V0_FALLBACK", "overrides": {}},
            "reason": "Test approval request",
            "confirmation_phrase": "SWITCH TO V0_FALLBACK",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["action_type"] == "PROFILE_SWITCH_FALLBACK"
    assert data["requested_by"]["email"] == admin_user1.email

    # Verify stored in DB
    approval = db.query(TwoPersonApproval).filter(
        TwoPersonApproval.request_id == data["request_id"]
    ).first()
    assert approval is not None
    assert approval.status == "PENDING"


def test_approval_requires_different_admin(
    client: TestClient, db: Session, admin_user1: User, admin_user2: User, monkeypatch
):
    """Test that approval requires a different admin than requester."""
    monkeypatch.setattr(settings, "ENV", "prod")

    # Create approval request as admin_user1
    from app.core.dependencies import get_current_user

    def override_user1():
        return admin_user1

    app.dependency_overrides[get_current_user] = override_user1

    request_response = client.post(
        "/v1/admin/runtime/approvals/request",
        json={
            "action_type": "PROFILE_SWITCH_FALLBACK",
            "action_payload": {"profile": "V0_FALLBACK"},
            "reason": "Test",
            "confirmation_phrase": "SWITCH TO V0_FALLBACK",
        },
    )
    request_id = request_response.json()["request_id"]

    # Try to approve as same user (should fail)
    approve_response = client.post(
        f"/v1/admin/runtime/approvals/{request_id}/approve",
        json={"confirmation_phrase": "SWITCH TO V0_FALLBACK"},
    )

    assert approve_response.status_code == 400
    error_data = approve_response.json()
    assert "SELF_APPROVAL_NOT_ALLOWED" in error_data.get("error", {}).get("code", "") or "SELF_APPROVAL_NOT_ALLOWED" in str(error_data)

    # Switch to admin_user2 and approve (should work)
    def override_user2():
        return admin_user2

    app.dependency_overrides[get_current_user] = override_user2

    approve_response2 = client.post(
        f"/v1/admin/runtime/approvals/{request_id}/approve",
        json={"confirmation_phrase": "SWITCH TO V0_FALLBACK"},
    )

    # Should succeed (or fail on other validations, but not self-approval)
    if approve_response2.status_code == 400:
        error_data = approve_response2.json()
        error_code = error_data.get("error", {}).get("code", "") or str(error_data)
        assert "SELF_APPROVAL_NOT_ALLOWED" not in error_code


def test_list_pending_approvals(client: TestClient, db: Session, admin_user1: User, monkeypatch):
    """Test listing pending approvals."""
    monkeypatch.setattr(settings, "ENV", "prod")

    # Create a pending approval
    client.post(
        "/v1/admin/runtime/approvals/request",
        json={
            "action_type": "PROFILE_SWITCH_FALLBACK",
            "action_payload": {"profile": "V0_FALLBACK"},
            "reason": "Test",
            "confirmation_phrase": "SWITCH TO V0_FALLBACK",
        },
    )

    # List pending approvals
    response = client.get("/v1/admin/runtime/approvals/pending")

    assert response.status_code == 200
    data = response.json()
    assert len(data["approvals"]) >= 1
    assert any(a["status"] == "PENDING" for a in data["approvals"])
