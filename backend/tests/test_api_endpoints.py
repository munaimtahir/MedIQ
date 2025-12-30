"""
API endpoint tests.
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def client():
    """Create a test client with temporary SQLite database."""
    # Create a temporary database file for each test
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    original_db_url = os.environ.get("DATABASE_URL")
    original_env = os.environ.get("ENV")
    original_skip_seed = os.environ.get("SKIP_SEED")
    
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ENV"] = "test"
    os.environ["SKIP_SEED"] = "true"
    
    try:
        # Import here to ensure environment variable is set before app initialization
        # Clear any cached imports
        import sys
        if "main" in sys.modules:
            del sys.modules["main"]
        if "database" in sys.modules:
            del sys.modules["database"]
        
        from main import app
        yield TestClient(app)
    finally:
        # Clean up
        os.close(db_fd)
        if os.path.exists(db_path):
            os.unlink(db_path)
        # Restore original environment variables
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        elif "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
        
        if original_env:
            os.environ["ENV"] = original_env
        elif "ENV" in os.environ:
            del os.environ["ENV"]
            
        if original_skip_seed:
            os.environ["SKIP_SEED"] = original_skip_seed
        elif "SKIP_SEED" in os.environ:
            del os.environ["SKIP_SEED"]


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

