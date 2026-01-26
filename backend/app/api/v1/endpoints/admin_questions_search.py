"""Admin search endpoints for questions."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.search import SearchMetaResponse, SearchResponse
from app.search.es_client import ping
from app.search.questions_search_service import search_questions_admin

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin_or_reviewer(user: User) -> None:
    """Require user to be ADMIN or REVIEWER."""
    if user.role not in ("ADMIN", "REVIEWER"):
        raise HTTPException(status_code=403, detail="Admin or Reviewer access required")


@router.get("/admin/questions/search", response_model=SearchResponse)
async def search_questions(
    q: str | None = Query(None, description="Search query string", max_length=200),
    year: int | None = Query(None, description="Filter by year"),
    block_id: str | None = Query(None, description="Filter by block ID"),
    theme_id: str | None = Query(None, description="Filter by theme ID"),
    topic_id: str | None = Query(None, description="Filter by topic ID"),
    concept_id: list[str] | None = Query(None, description="Filter by concept ID (repeatable)"),
    cognitive_level: list[str] | None = Query(None, description="Filter by cognitive level (repeatable)"),
    difficulty_label: list[str] | None = Query(None, description="Filter by difficulty (repeatable)"),
    source_book: list[str] | None = Query(None, description="Filter by source book (repeatable)"),
    status: list[str] | None = Query(None, description="Filter by status (repeatable)"),
    include_unpublished: bool = Query(False, description="Include unpublished questions"),
    sort: str = Query("relevance", description="Sort option: relevance, published_at_desc, updated_at_desc"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(25, ge=1, le=100, description="Page size (max 100)"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
) -> SearchResponse:
    """
    Search questions with full-text query + filters + facets (admin/reviewer only).

    Supports Elasticsearch with Postgres fallback.
    """
    require_admin_or_reviewer(current_user)

    # Validate sort
    valid_sorts = ["relevance", "published_at_desc", "updated_at_desc"]
    if sort not in valid_sorts:
        raise HTTPException(status_code=400, detail=f"Invalid sort. Must be one of: {', '.join(valid_sorts)}")

    # Validate query length
    if q and len(q) > 200:
        raise HTTPException(status_code=400, detail="Query string must be <= 200 characters")

    # Validate page_size
    if page_size > 100:
        raise HTTPException(status_code=400, detail="page_size must be <= 100")

    # Execute search
    try:
        result = search_questions_admin(
            db=db,
            user=current_user,
            q=q,
            year=year,
            block_id=block_id,
            theme_id=theme_id,
            topic_id=topic_id,
            concept_id=concept_id,
            cognitive_level=cognitive_level,
            difficulty_label=difficulty_label,
            source_book=source_book,
            status=status,
            include_unpublished=include_unpublished,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return SearchResponse(**result)
    except Exception as e:
        logger.error(f"Search endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/admin/questions/search/meta", response_model=SearchMetaResponse)
async def get_search_meta(
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> SearchMetaResponse:
    """
    Get search metadata including limits, engine status, and defaults (admin/reviewer only).
    """
    require_admin_or_reviewer(current_user)

    # Check ES reachability
    es_enabled = settings.ELASTICSEARCH_ENABLED
    es_reachable = False
    if es_enabled:
        try:
            es_reachable = ping()
        except Exception:
            pass

    return SearchMetaResponse(
        limits={"max_page_size": 100},
        engine={"enabled": es_enabled, "reachable": es_reachable},
        defaults={
            "include_unpublished_default": False,
            "status_defaults": ["PUBLISHED"],
        },
        sort_options=["relevance", "published_at_desc", "updated_at_desc"],
    )
