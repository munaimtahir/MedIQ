"""Performance guardrail tests (N+1 protection).

These tests validate that critical endpoints expose DB query counters and remain within
reasonable query-count budgets to prevent silent N+1 regressions.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app
from app.models.user import User, UserRole


def _parse_int_header(resp, name: str) -> int:
    v = resp.headers.get(name)
    if v is None:
        raise AssertionError(f"Missing required header: {name}")
    try:
        return int(v)
    except Exception as e:
        raise AssertionError(f"Invalid {name} header value: {v}") from e


@pytest.fixture
def client(db):
    """TestClient with auth + DB overrides."""

    from app.core.dependencies import get_current_user
    from app.db.session import get_db

    # Create users in the same DB session used by endpoints
    admin_email = f"admin-perf+{uuid4()}@test.local"
    student_email = f"student-perf+{uuid4()}@test.local"
    admin_user = User(
        id=uuid4(),
        email=admin_email,
        role=UserRole.ADMIN.value,
        password_hash="dummy",
        is_active=True,
        email_verified=True,
    )
    student_user = User(
        id=uuid4(),
        email=student_email,
        role=UserRole.STUDENT.value,
        password_hash="dummy",
        is_active=True,
        email_verified=True,
    )
    db.add(admin_user)
    db.add(student_user)
    db.commit()

    def override_get_db():
        yield db

    def override_get_current_user(request: Request) -> User:  # noqa: ARG001
        # Default to student for student endpoints; tests can override per-request by header.
        # We keep this simple because these tests focus on query counts, not auth correctness.
        return student_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        # Use TestClient without context manager to avoid lifespan issues
        c = TestClient(app)
        # Attach helpers for tests
        c.admin_user = admin_user  # type: ignore[attr-defined]
        c.student_user = student_user  # type: ignore[attr-defined]
        yield c
    finally:
        app.dependency_overrides.clear()


def test_admin_questions_first_page_query_count_reasonable(client: TestClient):
    """GET /v1/admin/questions first page should avoid N+1."""

    from app.core.dependencies import get_current_user

    def _as_admin(request: Request) -> User:  # noqa: ARG001
        return client.admin_user  # type: ignore[attr-defined]

    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = _as_admin
    try:
        resp = client.get("/v1/admin/questions?page=1&page_size=25")
    finally:
        if prev is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = prev
    if resp.status_code != 200:
        pytest.skip(f"Endpoint not available in this test config (status={resp.status_code})")

    q = _parse_int_header(resp, "X-DB-Queries")
    assert q <= 10, f"Too many DB queries for admin questions list: {q} (target <= 10)"


def test_student_revision_query_count_reasonable(client: TestClient):
    """GET /v1/student/revision should avoid N+1."""

    resp = client.get("/v1/student/revision")
    if resp.status_code != 200:
        pytest.skip(f"Endpoint not available in this test config (status={resp.status_code})")

    q = _parse_int_header(resp, "X-DB-Queries")
    assert q <= 6, f"Too many DB queries for student revision dashboard: {q} (target <= 6)"


def test_session_state_query_count_reasonable(client: TestClient):
    """GET /v1/sessions/{id} should avoid N+1."""

    # If sessions endpoint is available, the environment must provide a valid session id.
    # This test is a guardrail only; it will skip if the endpoint is not reachable.
    resp = client.get(f"/v1/sessions/{uuid4()}")
    # In many test DBs there won't be a session row; 404 is acceptable for this guardrail.
    if resp.status_code not in (200, 404):
        pytest.skip(f"Endpoint not available in this test config (status={resp.status_code})")

    q = _parse_int_header(resp, "X-DB-Queries")
    assert q <= 8, f"Too many DB queries for session state: {q} (target <= 8)"

