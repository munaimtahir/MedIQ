"""Admin dashboard endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.question_cms import Question, QuestionStatus
from app.models.syllabus import Block, Theme, Year
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
    years_count = db.query(func.count(Year.id)).filter(Year.is_active.is_(True)).scalar() or 0
    blocks_count = db.query(func.count(Block.id)).filter(Block.is_active.is_(True)).scalar() or 0
    themes_count = db.query(func.count(Theme.id)).filter(Theme.is_active.is_(True)).scalar() or 0

    # Question counts (CMS questions)
    published_count = (
        db.query(func.count(Question.id))
        .filter(Question.status == QuestionStatus.PUBLISHED)
        .scalar()
        or 0
    )
    in_review_count = (
        db.query(func.count(Question.id))
        .filter(Question.status == QuestionStatus.IN_REVIEW)
        .scalar()
        or 0
    )
    draft_count = (
        db.query(func.count(Question.id)).filter(Question.status == QuestionStatus.DRAFT).scalar()
        or 0
    )

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
