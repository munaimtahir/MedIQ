"""Admin endpoints for managing questions."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.common.pagination import PaginatedResponse, PaginationParams, pagination_params
from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.question import QuestionLegacy as Question
from app.models.syllabus import Theme
from app.models.user import User, UserRole
from app.schemas.question import (
    QuestionCreate,
    QuestionLegacyListItem,
    QuestionResponse,
    QuestionUpdate,
)

router = APIRouter(prefix="/admin/questions-legacy", tags=["Admin - Questions (Legacy)"])


# ============================================================================
# Questions CRUD
# ============================================================================


@router.get(
    "",
    response_model=PaginatedResponse[QuestionLegacyListItem],
    summary="List questions",
    description="List all questions with optional filtering and pagination.",
)
async def list_questions(
    pagination: PaginationParams = Depends(pagination_params),
    published: bool | None = Query(None, description="Filter by published status"),
    theme_id: int | None = Query(None, gt=0, description="Filter by theme ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> PaginatedResponse[QuestionLegacyListItem]:
    """List all questions (admin view - includes all statuses)."""
    query = db.query(Question)

    # Apply filters
    if published is not None:
        query = query.filter(Question.is_published == published)
    if theme_id is not None:
        query = query.filter(Question.theme_id == theme_id)

    # Apply pagination
    total = query.count()
    questions = query.offset(pagination.offset).limit(pagination.page_size).all()

    items: list[QuestionLegacyListItem] = []
    for q in questions:
        text = (q.question_text or "").strip()
        snippet = (text[:200] + "…") if len(text) > 200 else (text or "")
        items.append(
            QuestionLegacyListItem(
                question_id=q.id,
                stem_snippet=snippet,
                status="PUBLISHED" if q.is_published else "DRAFT",
                theme_id=q.theme_id,
                difficulty=q.difficulty,
                cognitive=None,
                updated_at=q.updated_at,
            )
        )

    return PaginatedResponse(
        items=items,
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.post(
    "",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create question",
    description="Create a new question.",
)
async def create_question(
    question_data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> QuestionResponse:
    """Create a new question."""
    # Verify theme exists
    theme = db.query(Theme).filter(Theme.id == question_data.theme_id).first()
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    # Validate options (must have exactly 5)
    if len(question_data.options) != 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question must have exactly 5 options",
        )

    # Validate correct_option_index (must be 0-4)
    if question_data.correct_option_index < 0 or question_data.correct_option_index > 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Correct option index must be between 0 and 4",
        )

    # Create question
    question = Question(
        theme_id=question_data.theme_id,
        question_text=question_data.question_text,
        options=question_data.options,
        correct_option_index=question_data.correct_option_index,
        explanation=question_data.explanation,
        tags=question_data.tags,
        difficulty=question_data.difficulty,
        is_published=question_data.is_published,
    )

    try:
        db.add(question)
        db.commit()
        db.refresh(question)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create question: {str(e)}",
        ) from e

    return QuestionResponse.model_validate(question)


@router.get(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Get question",
    description="Get a question by ID.",
)
async def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> QuestionResponse:
    """Get a question by ID."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    return QuestionResponse.model_validate(question)


@router.put(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Update question",
    description="Update a question.",
)
async def update_question(
    question_id: int,
    question_data: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> QuestionResponse:
    """Update a question."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    # Verify theme exists if being updated
    if question_data.theme_id is not None:
        theme = db.query(Theme).filter(Theme.id == question_data.theme_id).first()
        if not theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found",
            )

    # Validate options if being updated
    if question_data.options is not None:
        if len(question_data.options) != 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Question must have exactly 5 options",
            )

    # Validate correct_option_index if being updated
    if question_data.correct_option_index is not None:
        if question_data.correct_option_index < 0 or question_data.correct_option_index > 4:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Correct option index must be between 0 and 4",
            )

    # Update fields
    update_data = question_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    try:
        db.commit()
        db.refresh(question)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update question: {str(e)}",
        ) from e

    return QuestionResponse.model_validate(question)


@router.post(
    "/{question_id}/publish",
    response_model=QuestionResponse,
    summary="Publish question",
    description="Publish a question. Requires tags to be set.",
)
async def publish_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> QuestionResponse:
    """Publish a question."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    # Validate tags are set before publishing
    if not question.tags or len(question.tags) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question must have tags before publishing",
        )

    question.is_published = True

    try:
        db.commit()
        db.refresh(question)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish question: {str(e)}",
        ) from e

    return QuestionResponse.model_validate(question)


@router.post(
    "/{question_id}/unpublish",
    response_model=QuestionResponse,
    summary="Unpublish question",
    description="Unpublish a question.",
)
async def unpublish_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> QuestionResponse:
    """Unpublish a question."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    question.is_published = False

    try:
        db.commit()
        db.refresh(question)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unpublish question: {str(e)}",
        ) from e

    return QuestionResponse.model_validate(question)
