"""Tests for audit completeness and police-mode enforcement."""

import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.core.audit import write_audit_critical
from app.models.question_cms import AuditLog
from app.security.critical_actions import CRITICAL_AUDIT_EVENTS, CRITICAL_ENDPOINTS
from app.security.police_mode import validate_police_confirm

# Base URL for the API (adjust if needed)
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/v1"


class TestAuditCompleteness:
    """Test that critical actions are always audited."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup for each test."""
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        yield
        await self.client.aclose()

    def test_write_audit_critical_requires_reason(self, db):
        """Test that write_audit_critical requires reason for critical actions."""
        from app.core.app_exceptions import AppError
        from fastapi import Request
        from starlette.datastructures import Headers
        
        user_id = uuid4()
        
        # Create a mock request
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/test",
                "headers": Headers({}),
            }
        )
        request.state.request_id = "test-request-id"
        
        # Should raise ValueError if reason is missing for critical action
        with pytest.raises(ValueError, match="Reason is required"):
            write_audit_critical(
                db=db,
                actor_user_id=user_id,
                actor_role="ADMIN",
                action="EMAIL_MODE_SWITCH",  # Critical action
                entity_type="EMAIL_RUNTIME",
                entity_id=uuid4(),
                reason="",  # Empty reason should fail
                request=request,
            )

    def test_write_audit_critical_includes_all_fields(self, db):
        """Test that write_audit_critical includes all required fields."""
        from fastapi import Request
        from starlette.datastructures import Headers
        from app.models.user import User, UserRole
        from app.core.security import hash_password
        
        # Create a user first to satisfy foreign key constraint
        user_id = uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            password_hash=hash_password("Test123!"),
            full_name="Test User",
            role=UserRole.ADMIN.value,
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        db.commit()
        
        entity_id = uuid4()
        
        # Create a mock request
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/test",
                "headers": Headers({}),
            }
        )
        request.state.request_id = "test-request-id"
        request.state.police_reason = "Test reason"
        
        audit_entry = write_audit_critical(
            db=db,
            actor_user_id=user_id,
            actor_role="ADMIN",
            action="EMAIL_MODE_SWITCH",
            entity_type="EMAIL_RUNTIME",
            entity_id=entity_id,
            reason="Test reason",
            request=request,
            before={"mode": "shadow"},
            after={"mode": "active"},
            meta={"custom": "data"},
        )
        
        db.commit()
        db.refresh(audit_entry)
        
        # Verify all fields are present
        assert audit_entry.actor_user_id == user_id
        assert audit_entry.action == "EMAIL_MODE_SWITCH"
        assert audit_entry.entity_type == "EMAIL_RUNTIME"
        assert audit_entry.entity_id == entity_id
        assert audit_entry.meta is not None
        assert audit_entry.meta.get("request_id") == "test-request-id"
        assert audit_entry.meta.get("reason") == "Test reason"
        assert audit_entry.meta.get("actor_role") == "ADMIN"
        assert audit_entry.before == {"mode": "shadow"}
        assert audit_entry.after == {"mode": "active"}


class TestPoliceMode:
    """Test police-mode validation."""

    def test_validate_police_confirm_validates_phrase(self):
        """Test that validate_police_confirm validates phrase exactly."""
        from fastapi import Request
        from starlette.datastructures import Headers
        from app.core.app_exceptions import AppError
        
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/test",
                "headers": Headers({}),
            }
        )
        
        # Valid confirmation
        reason = validate_police_confirm(
            request,
            "DRAIN EMAIL OUTBOX",
            "Test reason",
            "DRAIN EMAIL OUTBOX",
        )
        assert reason == "Test reason"
        assert getattr(request.state, "police_reason") == "Test reason"
        
        # Invalid confirmation phrase
        with pytest.raises(AppError) as exc_info:
            validate_police_confirm(
                request,
                "WRONG PHRASE",
                "Test reason",
                "DRAIN EMAIL OUTBOX",
            )
        assert exc_info.value.code == "INVALID_CONFIRMATION_PHRASE"
        
        # Missing reason
        with pytest.raises(AppError) as exc_info:
            validate_police_confirm(
                request,
                "DRAIN EMAIL OUTBOX",
                "",
                "DRAIN EMAIL OUTBOX",
            )
        assert exc_info.value.code == "REASON_REQUIRED"


class TestAdminFreeze:
    """Test admin freeze functionality."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup for each test."""
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        yield
        await self.client.aclose()

    @patch("app.security.admin_freeze.get_admin_freeze_config")
    def test_check_admin_freeze_raises_423_when_frozen(self, mock_get_config):
        """Test that check_admin_freeze raises 423 when admin_freeze is enabled."""
        from app.security.admin_freeze import check_admin_freeze
        from app.models.admin_security import AdminSecurityRuntime
        from app.core.app_exceptions import AppError
        from sqlalchemy.orm import Session
        
        # Mock frozen config
        frozen_config = AdminSecurityRuntime(
            id=1,
            admin_freeze=True,
            freeze_reason="Emergency maintenance",
        )
        mock_get_config.return_value = frozen_config
        
        # Mock db session
        mock_db = MagicMock(spec=Session)
        
        # Should raise 423
        with pytest.raises(AppError) as exc_info:
            check_admin_freeze(mock_db)
        
        assert exc_info.value.status_code == 423
        assert exc_info.value.code == "ADMIN_FREEZE"
        assert "reason" in exc_info.value.details

    @patch("app.security.admin_freeze.get_admin_freeze_config")
    def test_check_admin_freeze_allows_when_not_frozen(self, mock_get_config):
        """Test that check_admin_freeze allows when admin_freeze is disabled."""
        from app.security.admin_freeze import check_admin_freeze
        from app.models.admin_security import AdminSecurityRuntime
        from sqlalchemy.orm import Session
        
        # Mock unfrozen config
        unfrozen_config = AdminSecurityRuntime(
            id=1,
            admin_freeze=False,
        )
        mock_get_config.return_value = unfrozen_config
        
        # Mock db session
        mock_db = MagicMock(spec=Session)
        
        # Should not raise
        check_admin_freeze(mock_db)  # Should complete without error


class TestCriticalEndpointsEnforcement:
    """Test that critical endpoints are properly protected."""

    def test_critical_events_listed(self):
        """Test that all critical events are defined."""
        assert len(CRITICAL_AUDIT_EVENTS) > 0
        assert "EMAIL_MODE_SWITCH" in CRITICAL_AUDIT_EVENTS
        assert "EMAIL_OUTBOX_DRAIN" in CRITICAL_AUDIT_EVENTS
        assert "NOTIFICATION_BROADCAST" in CRITICAL_AUDIT_EVENTS
        assert "ALGO_MODE_SWITCH" in CRITICAL_AUDIT_EVENTS
        assert "ADMIN_FREEZE_CHANGED" in CRITICAL_AUDIT_EVENTS

    def test_critical_endpoints_listed(self):
        """Test that critical endpoints are defined."""
        assert len(CRITICAL_ENDPOINTS) > 0
        
        # Check that key endpoints are listed
        endpoint_paths = [ep[0] for ep in CRITICAL_ENDPOINTS]
        assert any("email/outbox/drain" in ep for ep in endpoint_paths)
        assert any("notifications/broadcast" in ep for ep in endpoint_paths)
        assert any("algorithms/runtime/switch" in ep for ep in endpoint_paths)
