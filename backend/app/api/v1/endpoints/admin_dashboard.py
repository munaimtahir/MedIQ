"""Admin dashboard endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.syllabus import Block, Theme, Year
from app.models.question import Question
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin/dashboard", tags=["Admin - Dashboard"])


@router.get(
    "/summary",
    summary="Get dashboard summary",
    description="Get summary statistics for the admin dashboard.",
)
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> dict:
    """
    Get dashboard summary statistics.
    Returns counts for syllabus, content, and imports.
    """
    # Syllabus counts
    years_count = db.query(func.count(Year.id)).filter(Year.is_active == True).scalar() or 0
    blocks_count = db.query(func.count(Block.id)).filter(Block.is_active == True).scalar() or 0
    themes_count = db.query(func.count(Theme.id)).filter(Theme.is_active == True).scalar() or 0

    # Question counts (if available)
    published_count = (
        db.query(func.count(Question.id))
        .filter(Question.is_published == True)
        .scalar() or 0
    )
    # In review and draft counts can be added when those statuses are implemented
    in_review_count = None
    draft_count = None

    return {
        "syllabus": {
            "years": years_count,
            "blocks": blocks_count,
            "themes": themes_count,
        },
        "content": {
            "published": published_count,
            "in_review": in_review_count,
            "draft": draft_count,
        },
        "imports": {
            "last_import_at": None,
            "failed_rows": None,
        },
    }
