"""API v1 router - includes all v1 endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_academic,
    admin_audit,
    admin_dashboard,
    admin_import,
    admin_media,
    admin_questions,
    admin_questions_cms,
    admin_settings,
    admin_syllabus,
    admin_system,
    admin_users,
    analytics,
    auth,
    bkt,
    bookmarks,
    difficulty,
    health,
    learning,
    mfa,
    mistakes,
    oauth,
    onboarding,
    revision,
    sessions,
    srs,
    syllabus,
    telemetry,
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
api_router.include_router(admin_questions_cms.router, prefix="", tags=["Admin - Questions CMS"])
api_router.include_router(admin_import.router, prefix="", tags=["Admin - Import"])
api_router.include_router(admin_media.router, prefix="", tags=["Admin - Media"])
api_router.include_router(admin_audit.router, prefix="", tags=["Admin - Audit"])
api_router.include_router(admin_dashboard.router, prefix="", tags=["Admin - Dashboard"])
api_router.include_router(admin_settings.router, prefix="", tags=["Admin - Settings"])
api_router.include_router(admin_system.router, prefix="", tags=["Admin - System"])
api_router.include_router(admin_users.router, prefix="", tags=["Admin - Users"])
api_router.include_router(sessions.router, prefix="/v1", tags=["Sessions"])
api_router.include_router(bookmarks.router, prefix="/v1", tags=["Bookmarks"])
api_router.include_router(telemetry.router, prefix="/v1", tags=["Telemetry"])
api_router.include_router(analytics.router, prefix="/v1", tags=["Analytics"])
api_router.include_router(learning.router, prefix="/v1/learning", tags=["Learning Engine"])
api_router.include_router(bkt.router, prefix="/v1/learning/bkt", tags=["BKT Mastery"])
api_router.include_router(srs.router, prefix="/v1/learning/srs", tags=["SRS Queue"])
api_router.include_router(
    difficulty.router, prefix="/v1/learning/difficulty", tags=["Difficulty Calibration"]
)
api_router.include_router(revision.router, prefix="/v1", tags=["Revision"])
api_router.include_router(mistakes.router, prefix="/v1", tags=["Mistakes"])

# Include notifications router if available
try:
    from app.api.v1.endpoints import notifications

    api_router.include_router(notifications.router, prefix="/v1", tags=["Notifications"])
except ImportError:
    pass  # Notifications endpoint is optional
