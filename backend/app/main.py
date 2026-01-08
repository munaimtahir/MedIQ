"""FastAPI application factory and main entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.common.request_id import RequestIDMiddleware
from app.core.config import settings
from app.core.errors import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.redis_client import init_redis
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.seed_auth import seed_demo_accounts
from app.core.seed_syllabus import seed_syllabus_structure
from app.db.base import Base
from app.db.engine import engine
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()
    # Initialize Redis
    init_redis()
    # Create tables (in production, use migrations)
    if settings.ENV == "dev":
        Base.metadata.create_all(bind=engine)
    # Seed demo accounts if enabled
    seed_demo_accounts()
    # Seed syllabus structure (years and blocks) if empty
    db = SessionLocal()
    try:
        from app.models.syllabus import Year
        year_count = db.query(Year).count()
        if year_count == 0:
            print("No years found, seeding syllabus structure...")
            seed_syllabus_structure(db)
            print("Syllabus structure seeded successfully")
    except Exception as e:
        print(f"Error seeding syllabus structure: {e}")
    finally:
        db.close()
    yield
    # Shutdown
    pass


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="Medical Exam Platform API - Production-ready FastAPI backend",
        openapi_url="/openapi.json" if settings.ENV != "prod" else None,
        docs_url="/docs" if settings.ENV != "prod" else None,
        redoc_url="/redoc" if settings.ENV != "prod" else None,
        lifespan=lifespan,
    )

    # Add middleware (order matters - first added is outermost)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Include API routers
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint - API information."""
        return {
            "message": settings.PROJECT_NAME,
            "version": "1.0.0",
            "docs_url": "/docs" if settings.ENV != "prod" else None,
        }

    # Health endpoint at root level (for convenience)
    @app.get("/health", tags=["Health"])
    async def health():
        """Health check endpoint - returns 200 if the API is running."""
        return {"status": "ok"}

    return app


# Create app instance
app = create_app()
