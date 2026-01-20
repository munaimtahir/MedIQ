"""CMS Question service with workflow, validation, and versioning."""

from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.versioning import create_version, snapshot_question
from app.models.question_cms import ChangeKind, Question, QuestionStatus
from app.models.user import User, UserRole
from app.schemas.question_cms import QuestionCreate, QuestionUpdate


class QuestionWorkflowError(Exception):
    """Custom exception for workflow errors."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def validate_options(question: Question | QuestionCreate | QuestionUpdate) -> None:
    """Validate that exactly 5 non-empty options are present."""
    options = [
        getattr(question, "option_a"),
        getattr(question, "option_b"),
        getattr(question, "option_c"),
        getattr(question, "option_d"),
        getattr(question, "option_e"),
    ]

    # Check all options are present and non-empty
    if not all(options):
        raise QuestionWorkflowError("All 5 options (A-E) must be provided and non-empty")

    # Check correct_index is valid
    if hasattr(question, "correct_index") and question.correct_index is not None:
        if question.correct_index < 0 or question.correct_index > 4:
            raise QuestionWorkflowError("correct_index must be between 0 and 4")


def validate_submit(question: Question) -> None:
    """Validate question can be submitted (DRAFT -> IN_REVIEW)."""
    if question.status != QuestionStatus.DRAFT:
        raise QuestionWorkflowError(f"Cannot submit question with status {question.status.value}")

    # Required fields for submit
    if not question.stem:
        raise QuestionWorkflowError("stem is required before submission")
    validate_options(question)
    if question.correct_index is None:
        raise QuestionWorkflowError("correct_index is required before submission")
    if not question.year_id:
        raise QuestionWorkflowError("year_id is required before submission")
    if not question.block_id:
        raise QuestionWorkflowError("block_id is required before submission")
    if not question.theme_id:
        raise QuestionWorkflowError("theme_id is required before submission")
    if not question.difficulty:
        raise QuestionWorkflowError("difficulty is required before submission")
    if not question.cognitive_level:
        raise QuestionWorkflowError("cognitive_level is required before submission")


def validate_approve(question: Question) -> None:
    """Validate question can be approved (IN_REVIEW -> APPROVED)."""
    if question.status != QuestionStatus.IN_REVIEW:
        raise QuestionWorkflowError(f"Cannot approve question with status {question.status.value}")

    # All submit checks plus explanation
    validate_submit(question)
    if not question.explanation_md:
        raise QuestionWorkflowError("explanation_md is required before approval")


def validate_publish(question: Question) -> None:
    """Validate question can be published (APPROVED -> PUBLISHED)."""
    if question.status != QuestionStatus.APPROVED:
        raise QuestionWorkflowError(f"Cannot publish question with status {question.status.value}")

    # All approve checks plus source
    validate_approve(question)
    if not question.source_book:
        raise QuestionWorkflowError("source_book is required before publishing")
    if not question.source_page:
        raise QuestionWorkflowError("source_page is required before publishing")


def validate_status_transition(
    current_status: QuestionStatus, new_status: QuestionStatus, user_role: UserRole
) -> None:
    """Validate that a status transition is allowed."""
    allowed_transitions = {
        QuestionStatus.DRAFT: [QuestionStatus.IN_REVIEW],
        QuestionStatus.IN_REVIEW: [QuestionStatus.APPROVED, QuestionStatus.DRAFT],
        QuestionStatus.APPROVED: [QuestionStatus.PUBLISHED],
        QuestionStatus.PUBLISHED: [QuestionStatus.APPROVED],
    }

    if new_status not in allowed_transitions.get(current_status, []):
        raise QuestionWorkflowError(
            f"Invalid status transition from {current_status.value} to {new_status.value}"
        )

    # RBAC checks
    if new_status == QuestionStatus.PUBLISHED and user_role not in [UserRole.ADMIN]:
        raise QuestionWorkflowError("Only ADMIN can publish questions")
    if new_status == QuestionStatus.APPROVED and user_role not in [UserRole.ADMIN, UserRole.REVIEWER]:
        raise QuestionWorkflowError("Only ADMIN or REVIEWER can approve questions")


def create_question(
    db: Session,
    question_data: QuestionCreate,
    created_by: UUID,
    request: Request | None = None,
) -> Question:
    """Create a new question with versioning and audit."""
    question = Question(
        stem=question_data.stem,
        option_a=question_data.option_a,
        option_b=question_data.option_b,
        option_c=question_data.option_c,
        option_d=question_data.option_d,
        option_e=question_data.option_e,
        correct_index=question_data.correct_index,
        explanation_md=question_data.explanation_md,
        year_id=question_data.year_id,
        block_id=question_data.block_id,
        theme_id=question_data.theme_id,
        topic_id=question_data.topic_id,
        concept_id=question_data.concept_id,
        cognitive_level=question_data.cognitive_level,
        difficulty=question_data.difficulty,
        source_book=question_data.source_book,
        source_page=question_data.source_page,
        source_ref=question_data.source_ref,
        status=QuestionStatus.DRAFT,
        created_by=created_by,
        updated_by=created_by,
    )

    db.add(question)
    db.flush()  # Get the ID

    # Create version snapshot
    snapshot = snapshot_question(question)
    create_version(
        db=db,
        question_id=question.id,
        change_kind=ChangeKind.CREATE,
        changed_by=created_by,
        snapshot=snapshot,
    )

    # Audit log
    meta = {}
    if request:
        meta["request_id"] = getattr(request.state, "request_id", None)
        meta["user_agent"] = request.headers.get("user-agent")
        meta["ip"] = request.client.host if request.client else None

    write_audit(
        db=db,
        actor_user_id=created_by,
        action="question.create",
        entity_type="QUESTION",
        entity_id=question.id,
        before=None,
        after=snapshot,
        meta=meta,
    )

    db.commit()
    db.refresh(question)
    return question


def update_question(
    db: Session,
    question_id: UUID,
    question_data: QuestionUpdate,
    updated_by: UUID,
    request: Request | None = None,
) -> Question:
    """Update a question with versioning and audit."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    # Snapshot before update
    before_snapshot = snapshot_question(question)

    # Update fields
    update_dict = question_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(question, field, value)

    question.updated_by = updated_by
    db.flush()

    # Snapshot after update
    after_snapshot = snapshot_question(question)

    # Create version
    create_version(
        db=db,
        question_id=question.id,
        change_kind=ChangeKind.EDIT,
        changed_by=updated_by,
        snapshot=after_snapshot,
    )

    # Audit log
    meta = {}
    if request:
        meta["request_id"] = getattr(request.state, "request_id", None)
        meta["user_agent"] = request.headers.get("user-agent")
        meta["ip"] = request.client.host if request.client else None

    write_audit(
        db=db,
        actor_user_id=updated_by,
        action="question.update",
        entity_type="QUESTION",
        entity_id=question.id,
        before=before_snapshot,
        after=after_snapshot,
        meta=meta,
    )

    db.commit()
    db.refresh(question)
    return question


def submit_question(
    db: Session,
    question_id: UUID,
    user: User,
    request: Request | None = None,
) -> Question:
    """Submit question for review (DRAFT -> IN_REVIEW)."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    validate_submit(question)
    validate_status_transition(question.status, QuestionStatus.IN_REVIEW, UserRole(user.role))

    before_snapshot = snapshot_question(question)
    question.status = QuestionStatus.IN_REVIEW
    question.updated_by = user.id
    db.flush()

    after_snapshot = snapshot_question(question)

    # Version
    create_version(
        db=db,
        question_id=question.id,
        change_kind=ChangeKind.STATUS_CHANGE,
        changed_by=user.id,
        snapshot=after_snapshot,
        change_reason="Submitted for review",
    )

    # Audit
    meta = {}
    if request:
        meta["request_id"] = getattr(request.state, "request_id", None)

    write_audit(
        db=db,
        actor_user_id=user.id,
        action="question.submit",
        entity_type="QUESTION",
        entity_id=question.id,
        before=before_snapshot,
        after=after_snapshot,
        meta=meta,
    )

    db.commit()
    db.refresh(question)
    return question


def approve_question(
    db: Session,
    question_id: UUID,
    user: User,
    request: Request | None = None,
) -> Question:
    """Approve question (IN_REVIEW -> APPROVED)."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    validate_approve(question)
    validate_status_transition(question.status, QuestionStatus.APPROVED, UserRole(user.role))

    before_snapshot = snapshot_question(question)
    question.status = QuestionStatus.APPROVED
    question.approved_by = user.id
    from datetime import datetime, timezone

    question.approved_at = datetime.now(timezone.utc)
    question.updated_by = user.id
    db.flush()

    after_snapshot = snapshot_question(question)

    # Version
    create_version(
        db=db,
        question_id=question.id,
        change_kind=ChangeKind.STATUS_CHANGE,
        changed_by=user.id,
        snapshot=after_snapshot,
        change_reason="Approved",
    )

    # Audit
    meta = {}
    if request:
        meta["request_id"] = getattr(request.state, "request_id", None)

    write_audit(
        db=db,
        actor_user_id=user.id,
        action="question.approve",
        entity_type="QUESTION",
        entity_id=question.id,
        before=before_snapshot,
        after=after_snapshot,
        meta=meta,
    )

    db.commit()
    db.refresh(question)
    return question


def reject_question(
    db: Session,
    question_id: UUID,
    user: User,
    reason: str,
    request: Request | None = None,
) -> Question:
    """Reject question (IN_REVIEW -> DRAFT)."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    if question.status != QuestionStatus.IN_REVIEW:
        raise QuestionWorkflowError(f"Cannot reject question with status {question.status.value}")

    validate_status_transition(question.status, QuestionStatus.DRAFT, UserRole(user.role))

    before_snapshot = snapshot_question(question)
    question.status = QuestionStatus.DRAFT
    question.updated_by = user.id
    db.flush()

    after_snapshot = snapshot_question(question)

    # Version
    create_version(
        db=db,
        question_id=question.id,
        change_kind=ChangeKind.STATUS_CHANGE,
        changed_by=user.id,
        snapshot=after_snapshot,
        change_reason=f"Rejected: {reason}",
    )

    # Audit
    meta = {"rejection_reason": reason}
    if request:
        meta["request_id"] = getattr(request.state, "request_id", None)

    write_audit(
        db=db,
        actor_user_id=user.id,
        action="question.reject",
        entity_type="QUESTION",
        entity_id=question.id,
        before=before_snapshot,
        after=after_snapshot,
        meta=meta,
    )

    db.commit()
    db.refresh(question)
    return question


def publish_question(
    db: Session,
    question_id: UUID,
    user: User,
    request: Request | None = None,
) -> Question:
    """Publish question (APPROVED -> PUBLISHED)."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    validate_publish(question)
    validate_status_transition(question.status, QuestionStatus.PUBLISHED, UserRole(user.role))

    before_snapshot = snapshot_question(question)
    question.status = QuestionStatus.PUBLISHED
    from datetime import datetime, timezone

    question.published_at = datetime.now(timezone.utc)
    question.updated_by = user.id
    db.flush()

    after_snapshot = snapshot_question(question)

    # Version
    create_version(
        db=db,
        question_id=question.id,
        change_kind=ChangeKind.PUBLISH,
        changed_by=user.id,
        snapshot=after_snapshot,
        change_reason="Published",
    )

    # Audit
    meta = {}
    if request:
        meta["request_id"] = getattr(request.state, "request_id", None)

    write_audit(
        db=db,
        actor_user_id=user.id,
        action="question.publish",
        entity_type="QUESTION",
        entity_id=question.id,
        before=before_snapshot,
        after=after_snapshot,
        meta=meta,
    )

    db.commit()
    db.refresh(question)
    return question


def unpublish_question(
    db: Session,
    question_id: UUID,
    user: User,
    request: Request | None = None,
) -> Question:
    """Unpublish question (PUBLISHED -> APPROVED)."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    if question.status != QuestionStatus.PUBLISHED:
        raise QuestionWorkflowError(f"Cannot unpublish question with status {question.status.value}")

    validate_status_transition(question.status, QuestionStatus.APPROVED, UserRole(user.role))

    before_snapshot = snapshot_question(question)
    question.status = QuestionStatus.APPROVED
    question.published_at = None
    question.updated_by = user.id
    db.flush()

    after_snapshot = snapshot_question(question)

    # Version
    create_version(
        db=db,
        question_id=question.id,
        change_kind=ChangeKind.UNPUBLISH,
        changed_by=user.id,
        snapshot=after_snapshot,
        change_reason="Unpublished",
    )

    # Audit
    meta = {}
    if request:
        meta["request_id"] = getattr(request.state, "request_id", None)

    write_audit(
        db=db,
        actor_user_id=user.id,
        action="question.unpublish",
        entity_type="QUESTION",
        entity_id=question.id,
        before=before_snapshot,
        after=after_snapshot,
        meta=meta,
    )

    db.commit()
    db.refresh(question)
    return question
