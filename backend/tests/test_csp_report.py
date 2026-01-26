"""Tests for CSP report endpoint."""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.csp_report import CSPReport
from app.models.user import User, UserRole


@pytest.fixture
def client(db: Session):
    """Create test client with database dependency override."""
    from app.db.session import get_db

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def test_csp_report_endpoint_accepts_valid_report(client: TestClient, db: Session):
    """Test that CSP report endpoint accepts and stores valid reports."""
    # Sample CSP violation report (CSP reporting API format)
    report_data = {
        "csp-report": {
            "document-uri": "https://example.com/page",
            "referrer": "https://example.com/",
            "blocked-uri": "https://evil.com/script.js",
            "violated-directive": "script-src",
            "effective-directive": "script-src",
            "original-policy": "default-src 'self'; script-src 'self'",
            "source-file": "https://example.com/app.js",
            "line-number": "42",
            "column-number": "10",
        }
    }
    
    response = client.post("/v1/security/csp-report", json=report_data)
    
    # Should return 204 No Content
    assert response.status_code == 204
    
    # Verify report was stored
    report = db.query(CSPReport).filter(
        CSPReport.document_uri == "https://example.com/page"
    ).first()
    
    assert report is not None
    assert report.blocked_uri == "https://evil.com/script.js"
    assert report.violated_directive == "script-src"
    assert report.source_file == "https://example.com/app.js"
    assert report.line_number == "42"
    assert report.column_number == "10"


def test_csp_report_endpoint_handles_camelcase_format(client: TestClient, db: Session):
    """Test that CSP report endpoint handles camelCase format (some browsers use this)."""
    report_data = {
        "csp-report": {
            "documentUri": "https://example.com/page",
            "blockedUri": "https://evil.com/script.js",
            "violatedDirective": "script-src",
            "effectiveDirective": "script-src",
            "originalPolicy": "default-src 'self'; script-src 'self'",
            "sourceFile": "https://example.com/app.js",
            "lineNumber": "42",
            "columnNumber": "10",
        }
    }
    
    response = client.post("/v1/security/csp-report", json=report_data)
    
    assert response.status_code == 204
    
    # Verify report was stored
    report = db.query(CSPReport).filter(
        CSPReport.document_uri == "https://example.com/page"
    ).first()
    
    assert report is not None
    assert report.blocked_uri == "https://evil.com/script.js"
    assert report.violated_directive == "script-src"


def test_csp_report_endpoint_handles_minimal_report(client: TestClient, db: Session):
    """Test that CSP report endpoint handles minimal reports (only required fields)."""
    report_data = {
        "csp-report": {
            "document-uri": "https://example.com/page",
            "blocked-uri": "https://evil.com/script.js",
            "violated-directive": "script-src",
        }
    }
    
    response = client.post("/v1/security/csp-report", json=report_data)
    
    assert response.status_code == 204
    
    # Verify report was stored
    report = db.query(CSPReport).filter(
        CSPReport.document_uri == "https://example.com/page"
    ).first()
    
    assert report is not None
    assert report.blocked_uri == "https://evil.com/script.js"
    assert report.violated_directive == "script-src"
    # Optional fields should be None
    assert report.source_file is None
    assert report.line_number is None


def test_csp_report_endpoint_rate_limited(client: TestClient):
    """Test that CSP report endpoint is rate-limited (basic check)."""
    report_data = {
        "csp-report": {
            "document-uri": "https://example.com/page",
            "blocked-uri": "https://evil.com/script.js",
            "violated-directive": "script-src",
        }
    }
    
    # Make many requests (rate limit is 100/min per IP)
    # This test just verifies the endpoint exists and accepts requests
    # Full rate limit testing would require Redis
    for _ in range(5):
        response = client.post("/v1/security/csp-report", json=report_data)
        assert response.status_code == 204


def test_csp_report_endpoint_stores_user_agent_and_ip(client: TestClient, db: Session):
    """Test that CSP report endpoint stores user agent and IP address."""
    report_data = {
        "csp-report": {
            "document-uri": "https://example.com/page",
            "blocked-uri": "https://evil.com/script.js",
            "violated-directive": "script-src",
        }
    }
    
    # Set custom headers
    headers = {
        "User-Agent": "Mozilla/5.0 Test Browser",
        "X-Forwarded-For": "192.168.1.100",
    }
    
    response = client.post("/v1/security/csp-report", json=report_data, headers=headers)
    
    assert response.status_code == 204
    
    # Verify metadata was stored
    report = db.query(CSPReport).filter(
        CSPReport.document_uri == "https://example.com/page"
    ).first()
    
    assert report is not None
    assert report.user_agent == "Mozilla/5.0 Test Browser"
    # IP extraction logic may vary, but should be present
    assert report.ip_address is not None
