"""API v1 router - includes all v1 endpoints."""

from fastapi import APIRouter

from app.cohorts import api as cohorts_api
from app.api.v1.endpoints import (
    admin_academic,
    admin_algorithms,
    admin_approvals,
    admin_audit,
    admin_dashboard,
    admin_email,
    admin_graph,
    admin_graph_revision,
    admin_import,
    admin_mocks,
    admin_ranking,
    admin_runtime,
    admin_security,
    admin_warehouse,
    admin_warehouse_readiness,
    admin_irt,
    admin_rank,
    admin_media,
    admin_perf,
    admin_queues,
    admin_questions,
    admin_questions_cms,
    admin_questions_search,
    admin_search,
    admin_settings,
    admin_syllabus,
    admin_system,
    admin_tag_quality,
    admin_users,
    analytics,
    auth,
    bkt,
    bookmarks,
    difficulty,
    eval,
    eval_timeseries,
    health,
    learning,
    mfa,
    mistakes,
    mistakes_v1,
    oauth,
    observability,
    onboarding,
    revision,
    revision_today,
    security,
    sessions,
    srs,
    student_graph,
    syllabus,
    telemetry,
    sync,
    test_packages,
    user_prefs,
)
from app.graph import api as graph_api

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="", tags=["Health"])
api_router.include_router(security.router, prefix="", tags=["Security"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(oauth.router, prefix="/auth/oauth", tags=["OAuth"])
api_router.include_router(mfa.router, prefix="/auth/mfa", tags=["MFA"])
api_router.include_router(onboarding.router, prefix="", tags=["Onboarding"])
api_router.include_router(admin_academic.router, prefix="", tags=["Admin - Academic Structure"])
api_router.include_router(syllabus.router, prefix="", tags=["Syllabus"])
api_router.include_router(admin_syllabus.router, prefix="", tags=["Admin - Syllabus"])
api_router.include_router(admin_questions.router, prefix="", tags=["Admin - Questions"])
api_router.include_router(admin_questions_cms.router, prefix="", tags=["Admin - Questions CMS"])
api_router.include_router(admin_questions_search.router, prefix="", tags=["Admin - Questions Search"])
api_router.include_router(admin_import.router, prefix="", tags=["Admin - Import"])
api_router.include_router(admin_media.router, prefix="", tags=["Admin - Media"])
api_router.include_router(admin_perf.router, prefix="", tags=["Admin - Performance"])
api_router.include_router(admin_email.router, prefix="", tags=["Admin - Email"])
api_router.include_router(admin_audit.router, prefix="", tags=["Admin - Audit"])
api_router.include_router(admin_security.router, prefix="", tags=["Admin - Security"])
api_router.include_router(admin_dashboard.router, prefix="", tags=["Admin - Dashboard"])
api_router.include_router(admin_settings.router, prefix="", tags=["Admin - Settings"])
api_router.include_router(admin_system.router, prefix="", tags=["Admin - System"])
api_router.include_router(admin_runtime.router, prefix="", tags=["Admin - Runtime Control"])
api_router.include_router(admin_approvals.router, prefix="", tags=["Admin - Runtime Approvals"])
api_router.include_router(admin_users.router, prefix="", tags=["Admin - Users"])
api_router.include_router(admin_algorithms.router, prefix="", tags=["Admin - Algorithms"])
api_router.include_router(admin_queues.router, prefix="", tags=["Admin - Queues"])
api_router.include_router(admin_tag_quality.router, prefix="", tags=["Admin - Tag Quality"])
api_router.include_router(admin_irt.router, prefix="", tags=["Admin - IRT (Shadow)"])
api_router.include_router(admin_rank.router, prefix="", tags=["Admin - Rank (Shadow)"])
api_router.include_router(admin_graph_revision.router, prefix="", tags=["Admin - Graph Revision (Shadow)"])
api_router.include_router(admin_graph.router, prefix="", tags=["Admin - Concept Graph (Shadow)"])
api_router.include_router(graph_api.router, prefix="/admin/graph", tags=["Admin - Graph Queries"])
api_router.include_router(admin_warehouse.router, prefix="", tags=["Admin - Warehouse Export"])
api_router.include_router(admin_warehouse_readiness.router, prefix="", tags=["Admin - Warehouse Readiness"])
api_router.include_router(admin_mocks.router, prefix="", tags=["Admin - Mock Blueprints"])
api_router.include_router(admin_ranking.router, prefix="", tags=["Admin - Ranking (Mock)"])
api_router.include_router(cohorts_api.router, prefix="", tags=["Admin - Cohort Analytics"])
api_router.include_router(admin_search.router, prefix="", tags=["Admin - Search"])
api_router.include_router(observability.router, prefix="", tags=["Observability"])
api_router.include_router(user_prefs.router, prefix="", tags=["User Preferences"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(test_packages.router, prefix="", tags=["Test Packages"])
api_router.include_router(sync.router, prefix="", tags=["Offline Sync"])
api_router.include_router(bookmarks.router, prefix="/bookmarks", tags=["Bookmarks"])
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["Telemetry"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(learning.router, prefix="/learning", tags=["Learning Engine"])
api_router.include_router(bkt.router, prefix="/learning/bkt", tags=["BKT Mastery"])
api_router.include_router(srs.router, prefix="/learning/srs", tags=["SRS Queue"])
api_router.include_router(
    difficulty.router, prefix="/learning/difficulty", tags=["Difficulty Calibration"]
)
api_router.include_router(revision.router, prefix="/revision", tags=["Revision"])
api_router.include_router(revision_today.router, prefix="", tags=["Revision"])
api_router.include_router(mistakes.router, prefix="/mistakes", tags=["Mistakes"])
api_router.include_router(mistakes_v1.router, prefix="", tags=["Mistakes v1"])
api_router.include_router(eval.router, prefix="", tags=["Evaluation Harness"])
api_router.include_router(eval_timeseries.router, prefix="", tags=["Evaluation Harness"])
api_router.include_router(student_graph.router, prefix="", tags=["Student - Concept Graph"])

# Include notifications routers
try:
    from app.api.v1.endpoints import notifications

    api_router.include_router(notifications.router, prefix="", tags=["Notifications"])
except ImportError:
    pass  # Notifications endpoint is optional

try:
    from app.api.v1.endpoints import admin_notifications

    api_router.include_router(admin_notifications.router, prefix="", tags=["Admin - Notifications"])
except ImportError:
    pass  # Admin notifications endpoint is optional
