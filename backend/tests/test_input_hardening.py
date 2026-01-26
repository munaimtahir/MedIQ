"""Tests for input hardening: body size limits, validation caps, import row cap."""

from __future__ import annotations

import io
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.main import app
from app.models.user import User, UserRole


@pytest.fixture
def admin_user(db: Session) -> User:
    """Admin user for import and other admin endpoints."""
    u = User(
        id=uuid4(),
        email="admin-input@test.local",
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
def client(db: Session, admin_user: User):
    """TestClient with DB and admin user override."""
    from app.core.dependencies import get_current_user
    from app.db.session import get_db

    def override_get_db():
        yield db

    def override_get_current_user(_: Request) -> User:
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


class TestBodySizeLimit:
    """413 Payload Too Large and body size middleware."""

    def test_oversized_payload_returns_413(self, client: TestClient):
        """POST body over limit returns 413 with PAYLOAD_TOO_LARGE."""
        with patch("app.middleware.body_size_limit.settings") as s:
            s.MAX_BODY_BYTES_DEFAULT = 100
            s.MAX_BODY_BYTES_IMPORT = 10_000_000
            body = b"x" * 101
            r = client.post(
                "/v1/auth/login",
                content=body,
                headers={"Content-Type": "application/json"},
            )
        assert r.status_code == 413
        data = r.json()
        assert "error" in data
        assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"
        assert data["error"]["message"]
        details = data["error"].get("details") or {}
        assert details.get("limit") == 100

    def test_normal_request_unchanged(self, client: TestClient):
        """Small POST is not rejected by body size middleware."""
        r = client.post(
            "/v1/auth/login",
            json={"email": "a@b.com", "password": "short"},
            headers={"Content-Type": "application/json"},
        )
        # 401/422 expected; must not be 413
        assert r.status_code != 413


class TestValidationCaps:
    """Pydantic max_length / validation limit errors."""

    def test_long_stem_fails_validation(self, client: TestClient):
        """question_text over 4000 chars returns 422 VALIDATION_LIMIT_EXCEEDED."""
        from app.schemas.question import STEM_MAX_LENGTH

        long_text = "x" * (STEM_MAX_LENGTH + 1)
        r = client.post(
            "/v1/admin/questions-legacy",
            json={
                "theme_id": 1,
                "question_text": long_text,
                "options": ["a", "b", "c", "d", "e"],
                "correct_option_index": 0,
            },
        )
        assert r.status_code == 422
        data = r.json()
        assert "error" in data
        assert data["error"]["code"] in (
            "VALIDATION_ERROR",
            "VALIDATION_LIMIT_EXCEEDED",
        )
        details = data["error"].get("details") or []
        if isinstance(details, list):
            fields = " ".join(str(d.get("field", "")) for d in details)
            assert "question_text" in fields or "string_too_long" in str(details)
        else:
            assert "details" in str(details) or "limit" in str(details)


class TestImportRowCap:
    """Import row count cap and VALIDATION_LIMIT_EXCEEDED."""

    @pytest.fixture
    def active_schema(self, client: TestClient):
        """Create a minimal active import schema via API."""
        mapping = {
            "year": {"column": "year"},
            "block": {"column": "block"},
            "theme": {"column": "theme"},
            "option_a": {"column": "A"},
            "option_b": {"column": "B"},
            "option_c": {"column": "C"},
            "option_d": {"column": "D"},
            "option_e": {"column": "E"},
            "correct": {"column": "correct"},
        }
        rules = {"required": ["year", "block", "theme", "correct"]}
        cr = client.post(
            "/v1/admin/import/schemas",
            json={
                "name": "test-cap",
                "file_type": "csv",
                "mapping_json": mapping,
                "rules_json": rules,
            },
        )
        assert cr.status_code == 201, cr.json()
        schema_id = cr.json()["id"]
        act = client.post(f"/v1/admin/import/schemas/{schema_id}/activate")
        assert act.status_code == 200
        return schema_id

    def test_import_row_cap_enforced(
        self, client: TestClient, active_schema: str
    ):
        """CSV with more than IMPORT_MAX_ROWS rows returns 422 VALIDATION_LIMIT_EXCEEDED."""
        with patch("app.api.v1.endpoints.admin_import.settings") as mock_settings:
            mock_settings.IMPORT_MAX_ROWS = 5
            mock_settings.MAX_BODY_BYTES_IMPORT = 10_000_000
            buf = io.BytesIO()
            buf.write(b"year,block,theme,A,B,C,D,E,correct\n")
            for _ in range(6):
                buf.write(b"1,A,Test Theme,opt1,opt2,opt3,opt4,opt5,0\n")
            buf.seek(0)
            files = {"file": ("cap.csv", buf, "text/csv")}
            data = {"dry_run": "true"}
            r = client.post(
                "/v1/admin/import/questions",
                data=data,
                files=files,
            )
        assert r.status_code == 422
        body = r.json()
        assert "error" in body
        assert body["error"]["code"] == "VALIDATION_LIMIT_EXCEEDED"
        details = body["error"].get("details") or {}
        assert details.get("limit") == 5
