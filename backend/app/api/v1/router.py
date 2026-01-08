"""API v1 router - includes all v1 endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_academic,
    admin_dashboard,
    admin_questions,
    admin_settings,
    admin_syllabus,
    admin_system,
    admin_users,
    auth,
    health,
    mfa,
    oauth,
    onboarding,
    syllabus,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(oauth.router, prefix="/auth/oauth", tags=["OAuth"])
api_router.include_router(mfa.router, prefix="/auth/mfa", tags=["MFA"])
api_router.include_router(onboarding.router, prefix="", tags=["Onboarding"])
api_router.include_router(admin_academic.router, prefix="", tags=["Admin - Academic Structure"])
api_router.include_router(syllabus.router, prefix="", tags=["Syllabus"])
api_router.include_router(admin_syllabus.router, prefix="", tags=["Admin - Syllabus"])
api_router.include_router(admin_questions.router, prefix="", tags=["Admin - Questions"])
api_router.include_router(admin_dashboard.router, prefix="", tags=["Admin - Dashboard"])
api_router.include_router(admin_settings.router, prefix="", tags=["Admin - Settings"])
api_router.include_router(admin_system.router, prefix="", tags=["Admin - System"])
api_router.include_router(admin_users.router, prefix="", tags=["Admin - Users"])

# Include notifications router if available
try:
    from app.api.v1.endpoints import notifications

    api_router.include_router(notifications.router, prefix="/v1", tags=["Notifications"])
except ImportError:
    pass  # Notifications endpoint is optional
