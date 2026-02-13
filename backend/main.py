"""Compatibility entrypoint.

This module keeps legacy commands like `uvicorn main:app` working, while routing
to the canonical JWT-based FastAPI app defined in `app.main`.
"""

from app.main import app, create_app

__all__ = ["app", "create_app"]
