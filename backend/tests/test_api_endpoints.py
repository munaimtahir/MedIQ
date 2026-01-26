"""
API endpoint tests.

NOTE: These tests are for legacy endpoints that may not exist in the current API structure.
The current API uses /v1/syllabus/blocks and /v1/syllabus/themes with authentication.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.skip(reason="Legacy endpoint - current API uses /v1/syllabus/blocks with auth")
def test_blocks_endpoint_returns_list():
    """Test that blocks endpoint returns a list."""
    response = client.get("/blocks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.skip(reason="Legacy endpoint - current API uses /v1/syllabus/blocks with auth")
def test_blocks_endpoint_with_year_filter():
    """Test that blocks endpoint accepts year filter."""
    response = client.get("/blocks?year=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.skip(reason="Legacy endpoint - current API uses /v1/syllabus/themes with auth")
def test_themes_endpoint_returns_list():
    """Test that themes endpoint returns a list."""
    response = client.get("/themes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.skip(reason="Legacy endpoint - current API uses /v1/syllabus/themes with auth")
def test_themes_endpoint_with_block_filter():
    """Test that themes endpoint accepts block_id filter."""
    response = client.get("/themes?block_id=A")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.skip(reason="Legacy endpoint - no public /questions endpoint exists")
def test_questions_endpoint_returns_list():
    """Test that questions endpoint returns a list."""
    response = client.get("/questions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.skip(reason="Legacy endpoint - no public /questions endpoint exists")
def test_questions_endpoint_with_limit():
    """Test that questions endpoint accepts limit parameter."""
    response = client.get("/questions?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 10
