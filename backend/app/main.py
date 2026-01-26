"""FastAPI application factory and main entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.redis_client import init_redis
from app.core.security_headers import SecurityHeadersMiddleware
from app.middleware.body_size_limit import BodySizeLimitMiddleware
from app.middleware.cache_headers import CacheHeadersMiddleware
from app.middleware.request_timing import RequestTimingMiddleware
from app.core.seed_academic import seed_academic_structure
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
    # Initialize Redis (skip in test mode to avoid connection attempts)
    if settings.ENV != "test":
        init_redis()
    # Create tables (in production, use migrations)
    # Disabled: Using Alembic migrations for all environments
    # if settings.ENV == "dev":
    #     Base.metadata.create_all(bind=engine)
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

    # Seed academic structure (onboarding years/blocks/subjects) if empty
    db = SessionLocal()
    try:
        from app.models.academic import AcademicYear

        academic_year_count = db.query(AcademicYear).count()
        if academic_year_count == 0:
            print("No academic years found, seeding academic structure...")
            seed_academic_structure(db)
            print("Academic structure seeded successfully")
    except Exception as e:
        print(f"Error seeding academic structure: {e}")
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
    # RequestTimingMiddleware must be outermost to guarantee headers even on exceptions.
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    # CORS: Deny-by-default with env allowlists (no wildcards)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.cors_allow_methods_list,
        allow_headers=settings.cors_allow_headers_list,
        expose_headers=settings.cors_expose_headers_list,
    )
    # Cache headers: Ensure API responses are never cached (CDN-safe)
    app.add_middleware(CacheHeadersMiddleware)

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
