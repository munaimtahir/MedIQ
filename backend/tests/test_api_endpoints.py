"""
API endpoint tests.
"""
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create a test client with in-memory SQLite database."""
    # Use in-memory SQLite for tests to avoid database connection issues
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    try:
        # Import here to ensure environment variable is set before app initialization
        from main import app
        yield TestClient(app)
    finally:
        # Restore original DATABASE_URL if it existed
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        elif "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]


def test_blocks_endpoint_returns_list(client):
    """Test that blocks endpoint returns a list."""
    response = client.get("/blocks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_blocks_endpoint_with_year_filter(client):
    """Test that blocks endpoint accepts year filter."""
    response = client.get("/blocks?year=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_themes_endpoint_returns_list(client):
    """Test that themes endpoint returns a list."""
    response = client.get("/themes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_themes_endpoint_with_block_filter(client):
    """Test that themes endpoint accepts block_id filter."""
    response = client.get("/themes?block_id=A")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_questions_endpoint_returns_list(client):
    """Test that questions endpoint returns a list."""
    response = client.get("/questions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_questions_endpoint_with_limit(client):
    """Test that questions endpoint accepts limit parameter."""
    response = client.get("/questions?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 10

