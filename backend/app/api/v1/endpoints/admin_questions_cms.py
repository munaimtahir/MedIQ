"""Admin CMS Question Bank endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.common.pagination import PaginatedResponse, PaginationParams, pagination_params
from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.question_cms import Question, QuestionVersion
from app.models.user import User, UserRole
from app.schemas.question_cms import (
    QuestionCreate,
    QuestionListOut,
    QuestionOut,
    QuestionUpdate,
    RejectRequest,
    VersionOut,
    WorkflowActionOut,
)
from app.services.question_cms import (
    QuestionWorkflowError,
    approve_question,
    create_question,
    publish_question,
    reject_question,
    submit_question,
    unpublish_question,
    update_question,
)

router = APIRouter(prefix="/admin/questions", tags=["Admin - Questions CMS"])


# ============================================================================
# Questions CRUD
# ============================================================================


@router.get(
    "",
    response_model=PaginatedResponse[QuestionListOut],
    summary="List questions",
    description="List questions with filtering, pagination, and search.",
)
async def list_questions(
    status: Annotated[
        str | None,
        Query(description="Filter by status (DRAFT, IN_REVIEW, APPROVED, PUBLISHED)"),
    ] = None,
    year_id: Annotated[int | None, Query(description="Filter by year ID")] = None,
    block_id: Annotated[int | None, Query(description="Filter by block ID")] = None,
    theme_id: Annotated[int | None, Query(description="Filter by theme ID")] = None,
    difficulty: Annotated[str | None, Query(description="Filter by difficulty")] = None,
    cognitive_level: Annotated[str | None, Query(description="Filter by cognitive level")] = None,
    source_book: Annotated[str | None, Query(description="Filter by source book")] = None,
    q: Annotated[str | None, Query(description="Text search on stem")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
    sort: Annotated[str, Query(description="Sort field (default: updated_at)")] = "updated_at",
    order: Annotated[str, Query(description="Sort order (asc/desc)")] = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> PaginatedResponse[QuestionListOut]:
    """List questions with filters and pagination."""
    query = db.query(Question)

    # Apply filters
    if status:
        from app.models.question_cms import QuestionStatus

        try:
            status_enum = QuestionStatus(status.upper())
            query = query.filter(Question.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}",
            ) from None
    if year_id:
        query = query.filter(Question.year_id == year_id)
    if block_id:
        query = query.filter(Question.block_id == block_id)
    if theme_id:
        query = query.filter(Question.theme_id == theme_id)
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    if cognitive_level:
        query = query.filter(Question.cognitive_level == cognitive_level)
    if source_book:
        query = query.filter(Question.source_book.ilike(f"%{source_book}%"))
    if q:
        query = query.filter(Question.stem.ilike(f"%{q}%"))

    # Apply sorting
    if sort == "updated_at":
        if order.lower() == "asc":
            query = query.order_by(Question.updated_at.asc())
        else:
            query = query.order_by(Question.updated_at.desc())
    elif sort == "created_at":
        if order.lower() == "asc":
            query = query.order_by(Question.created_at.asc())
        else:
            query = query.order_by(Question.created_at.desc())

    # Apply pagination
    total = query.count()
    questions = query.offset(pagination.offset).limit(pagination.page_size).all()

    items: list[QuestionListOut] = []
    for qobj in questions:
        stem = (qobj.stem or "").strip()
        snippet = (stem[:200] + "…") if len(stem) > 200 else (stem or None)
        items.append(
            QuestionListOut(
                id=qobj.id,
                status=qobj.status,
                stem=snippet,
                year_id=qobj.year_id,
                block_id=qobj.block_id,
                theme_id=qobj.theme_id,
                difficulty=qobj.difficulty,
                cognitive_level=qobj.cognitive_level,
                source_book=qobj.source_book,
                source_page=qobj.source_page,
                created_at=qobj.created_at,
                updated_at=qobj.updated_at,
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
    response_model=QuestionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create question",
    description="Create a new question (starts as DRAFT).",
)
async def create_question_endpoint(
    question_data: QuestionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> QuestionOut:
    """Create a new question."""
    question = create_question(db, question_data, current_user.id, request)
    return QuestionOut.model_validate(question)


@router.get(
    "/{question_id}",
    response_model=QuestionOut,
    summary="Get question",
    description="Get a question by ID.",
)
async def get_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> QuestionOut:
    """Get a question by ID."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return QuestionOut.model_validate(question)


@router.put(
    "/{question_id}",
    response_model=QuestionOut,
    summary="Update question",
    description="Update a question.",
)
async def update_question_endpoint(
    question_id: UUID,
    question_data: QuestionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> QuestionOut:
    """Update a question."""
    try:
        question = update_question(db, question_id, question_data, current_user.id, request)
        return QuestionOut.model_validate(question)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update question: {str(e)}",
        ) from e


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete question",
    description="Delete a question (hard delete).",
)
async def delete_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    """Delete a question."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    db.delete(question)
    db.commit()
    
    # Emit outbox event after commit (fail-open)
    try:
        from app.search.outbox_emit import emit_search_outbox_event
        from app.models.search_indexing import SearchOutboxEventType
        emit_search_outbox_event(
            db=db,
            event_type=SearchOutboxEventType.QUESTION_DELETED,
            question_id=question_id,
        )
    except Exception:
        # Fail-open: log but don't raise
        pass


# ============================================================================
# Workflow Actions
# ============================================================================


@router.post(
    "/{question_id}/submit",
    response_model=WorkflowActionOut,
    summary="Submit question",
    description="Submit question for review (DRAFT -> IN_REVIEW).",
)
async def submit_question_endpoint(
    question_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> WorkflowActionOut:
    """Submit question for review."""
    try:
        question = submit_question(db, question_id, current_user, request)
        return WorkflowActionOut(
            message="Question submitted for review",
            question_id=question.id,
            previous_status=question.status,  # This will be IN_REVIEW now
            new_status=question.status,
        )
    except QuestionWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit question: {str(e)}",
        ) from e


@router.post(
    "/{question_id}/approve",
    response_model=WorkflowActionOut,
    summary="Approve question",
    description="Approve question (IN_REVIEW -> APPROVED).",
)
async def approve_question_endpoint(
    question_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> WorkflowActionOut:
    """Approve question."""
    try:

        # Get current status before approval
        question_before = db.query(Question).filter(Question.id == question_id).first()
        if not question_before:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        previous_status = question_before.status

        question = approve_question(db, question_id, current_user, request)
        return WorkflowActionOut(
            message="Question approved",
            question_id=question.id,
            previous_status=previous_status,
            new_status=question.status,
        )
    except QuestionWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve question: {str(e)}",
        ) from e


@router.post(
    "/{question_id}/reject",
    response_model=WorkflowActionOut,
    summary="Reject question",
    description="Reject question (IN_REVIEW -> DRAFT).",
)
async def reject_question_endpoint(
    question_id: UUID,
    reject_data: RejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> WorkflowActionOut:
    """Reject question."""
    try:

        # Get current status before rejection
        question_before = db.query(Question).filter(Question.id == question_id).first()
        if not question_before:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        previous_status = question_before.status

        question = reject_question(db, question_id, current_user, reject_data.reason, request)
        return WorkflowActionOut(
            message="Question rejected",
            question_id=question.id,
            previous_status=previous_status,
            new_status=question.status,
        )
    except QuestionWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject question: {str(e)}",
        ) from e


@router.post(
    "/{question_id}/publish",
    response_model=WorkflowActionOut,
    summary="Publish question",
    description="Publish question (APPROVED -> PUBLISHED).",
)
async def publish_question_endpoint(
    question_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> WorkflowActionOut:
    """Publish question."""
    try:

        # Get current status before publish
        question_before = db.query(Question).filter(Question.id == question_id).first()
        if not question_before:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        previous_status = question_before.status

        question = publish_question(db, question_id, current_user, request)
        return WorkflowActionOut(
            message="Question published",
            question_id=question.id,
            previous_status=previous_status,
            new_status=question.status,
        )
    except QuestionWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish question: {str(e)}",
        ) from e


@router.post(
    "/{question_id}/unpublish",
    response_model=WorkflowActionOut,
    summary="Unpublish question",
    description="Unpublish question (PUBLISHED -> APPROVED).",
)
async def unpublish_question_endpoint(
    question_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> WorkflowActionOut:
    """Unpublish question."""
    try:

        # Get current status before unpublish
        question_before = db.query(Question).filter(Question.id == question_id).first()
        if not question_before:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        previous_status = question_before.status

        question = unpublish_question(db, question_id, current_user, request)
        return WorkflowActionOut(
            message="Question unpublished",
            question_id=question.id,
            previous_status=previous_status,
            new_status=question.status,
        )
    except QuestionWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unpublish question: {str(e)}",
        ) from e


# ============================================================================
# Version History
# ============================================================================


@router.get(
    "/{question_id}/versions",
    response_model=list[VersionOut],
    summary="List question versions",
    description="Get version history for a question.",
)
async def list_question_versions(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> list[VersionOut]:
    """Get version history for a question."""
    # Verify question exists
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    versions = (
        db.query(QuestionVersion)
        .filter(QuestionVersion.question_id == question_id)
        .order_by(QuestionVersion.version_no.desc())
        .all()
    )

    return [VersionOut.model_validate(v) for v in versions]


@router.get(
    "/{question_id}/versions/{version_id}",
    response_model=VersionOut,
    summary="Get question version",
    description="Get a specific version of a question.",
)
async def get_question_version(
    question_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> VersionOut:
    """Get a specific version of a question."""
    version = (
        db.query(QuestionVersion)
        .filter(QuestionVersion.id == version_id, QuestionVersion.question_id == question_id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    return VersionOut.model_validate(version)
