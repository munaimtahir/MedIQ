"""
Health check tests for the API.
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
        modules_to_clear = ["main", "database", "models", "seed"]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        from database import Base, engine
        # Ensure tables are created
        Base.metadata.create_all(bind=engine)
        
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


def test_root_endpoint(client):
    """Test that the root endpoint returns 200 and correct message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["message"] == "Medical Exam Platform API"
    assert data["version"] == "1.0.0"

