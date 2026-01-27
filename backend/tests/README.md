# Backend Test Suite

## Overview

This directory contains the pytest test suite for the FastAPI backend. Tests are organized by feature area and use async/await patterns for FastAPI endpoints.

## Test Structure

```
tests/
├── auth/              # Authentication and authorization tests
│   ├── test_login.py  # Login endpoint tests
│   └── test_rbac.py   # Role-based access control tests
├── helpers/           # Test helper utilities
│   └── seed.py        # Seed functions for creating test data
└── conftest.py        # Pytest fixtures and configuration
```

## Running Tests

### Local Development

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/auth/test_login.py

# Run specific test
pytest tests/auth/test_login.py::test_login_success

# Run with verbose output
pytest -v
```

### Docker Compose (Recommended)

```bash
# Run tests in isolated test environment
cd infra/docker/compose
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Run tests and view logs
docker compose -f docker-compose.test.yml up --build
docker compose -f docker-compose.test.yml logs -f backend_test
```

## Test Fixtures

### Database Fixtures

- `db`: Sync SQLAlchemy session with transaction rollback
- `db_session`: Async SQLAlchemy session with transaction rollback

### User Fixtures

- `test_user`: Creates a test student user
- `test_admin_user`: Creates a test admin user
- `auth_headers_student`: Authorization header for student user
- `auth_headers_admin`: Authorization header for admin user

### Client Fixtures

- `client`: Sync FastAPI TestClient
- `async_client`: Async httpx.AsyncClient for async endpoints

## Test Helpers

### Seed Functions

Located in `tests/helpers/seed.py`:

- `create_test_user()`: Create a user with custom attributes
- `create_test_student()`: Create a student user
- `create_test_admin()`: Create an admin user
- `create_test_reviewer()`: Create a reviewer user

Example:
```python
from tests.helpers.seed import create_test_student

user = create_test_student(
    db,
    email="student@example.com",
    password="TestPass123!",
    email_verified=True,
)
```

## Test Environment

Tests use a separate test database and Redis instance:

- **Database**: `exam_platform_test` (separate from dev database)
- **Redis**: Separate instance with no persistence
- **Environment**: `ENV=test` (disables external services)

## Writing Tests

### Async Endpoint Tests

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_my_endpoint(async_client: AsyncClient, db: Session):
    # Create test data
    user = create_test_student(db, email="test@example.com")
    db.commit()
    
    # Make request
    response = await async_client.get(
        "/v1/endpoint",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "value"
```

### Sync Endpoint Tests

```python
def test_my_sync_endpoint(client: TestClient, db: Session):
    # Create test data
    user = create_test_student(db)
    db.commit()
    
    # Make request
    response = client.get("/v1/endpoint")
    
    # Assertions
    assert response.status_code == 200
```

## Test Isolation

- Each test runs in a database transaction that is rolled back after the test
- Tests are isolated from each other
- No test data persists between test runs

## Coverage

Run tests with coverage:

```bash
pytest --cov=app --cov-report=html
```

Coverage report will be generated in `htmlcov/index.html`.

## Test Suites

### Auth Tests
- `tests/auth/test_login.py` - Login endpoint tests
- `tests/auth/test_rbac.py` - Role-based access control tests
- `tests/auth/test_refresh_token.py` - Refresh token endpoint tests ✅
- `tests/auth/test_token_revocation.py` - Logout/logout-all tests ✅
- `tests/auth/test_password_reset.py` - Password reset flow tests ✅
- `tests/auth/test_email_verification.py` - Email verification tests ✅
- `tests/auth/test_rate_limiting.py` - Rate limiting behavior tests ✅ **NEW**
- `tests/auth/test_validation_boundaries.py` - Data validation boundary tests ✅ **NEW**
- `tests/auth/test_permission_boundaries.py` - Permission boundaries and RBAC tests ✅
- `tests/auth/test_oauth.py` - OAuth endpoint tests ✅ **NEW**
- `tests/auth/test_mfa.py` - MFA flow tests ✅ **NEW**

### Property Tests
- `tests/property/test_session_invariants.py` - Session workflow invariants
- `tests/property/test_scoring_invariants.py` - Learning engine invariants
- `tests/property/test_cms_invariants.py` - CMS workflow invariants ✅

### Integration Tests
- `tests/integration/test_auth_session_flow.py` - Auth + Session integration ✅ **NEW**
- `tests/integration/test_cms_analytics_flow.py` - CMS + Analytics integration ✅ **NEW**
- `tests/integration/test_learning_session_flow.py` - Learning Engine + Session integration ✅ **NEW**

### Performance Tests
- `tests/performance/test_load_endpoints.py` - Load tests for critical endpoints ✅ **NEW**

## TODO (Task 162B)

- [x] Add tests for refresh token endpoint ✅
- [x] Add tests for token revocation ✅
- [x] Add tests for password reset flow ✅
- [x] Add tests for email verification ✅
- [x] Add integration tests for session creation ✅
- [x] Add integration tests for question submission ✅
- [x] Add tests for session expiry handling ✅
- [x] Add tests for concurrent session creation ✅
- [x] Add tests for rate limiting behavior ✅
- [x] Add tests for data validation boundaries ✅
- [x] Add tests for permission boundaries ✅
- [x] Add tests for learning engine edge cases ✅
- [x] Add tests for OAuth endpoints ✅
- [x] Add tests for MFA flow ✅
- [x] Add performance/load tests for critical endpoints ✅
- [x] Add integration tests spanning multiple services ✅
