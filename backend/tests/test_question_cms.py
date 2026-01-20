"""Tests for CMS Question Bank functionality."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from app.main import app
from app.models.question_cms import (
    Question as CMSQuestion,
    QuestionStatus,
    QuestionVersion,
    AuditLog,
)
from app.models.user import User, UserRole
from app.services.question_cms import (
    create_question,
    submit_question,
    approve_question,
    reject_question,
    publish_question,
    validate_submit,
    validate_approve,
    validate_publish,
    QuestionWorkflowError,
)
from app.schemas.question_cms import QuestionCreate

client = TestClient(app)


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user for testing."""
    user = User(
        id=uuid4(),
        name="Admin User",
        email="admin@test.com",
        role=UserRole.ADMIN.value,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def reviewer_user(db: Session) -> User:
    """Create a reviewer user for testing."""
    user = User(
        id=uuid4(),
        name="Reviewer User",
        email="reviewer@test.com",
        role=UserRole.REVIEWER.value,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_question_data() -> QuestionCreate:
    """Sample question data for testing."""
    return QuestionCreate(
        stem="What is 2+2?",
        option_a="3",
        option_b="4",
        option_c="5",
        option_d="6",
        option_e="7",
        correct_index=1,
        explanation_md="2+2 equals 4",
        year_id=1,
        block_id=1,
        theme_id=1,
        difficulty="easy",
        cognitive_level="recall",
    )


def test_create_question_draft(db: Session, admin_user: User, sample_question_data: QuestionCreate):
    """Test creating a question in DRAFT status."""
    question = create_question(db, sample_question_data, admin_user.id)

    assert question.status == QuestionStatus.DRAFT
    assert question.stem == sample_question_data.stem
    assert question.correct_index == sample_question_data.correct_index
    assert question.created_by == admin_user.id
    assert question.updated_by == admin_user.id

    # Check version was created
    versions = db.query(QuestionVersion).filter(QuestionVersion.question_id == question.id).all()
    assert len(versions) == 1
    assert versions[0].change_kind.value == "CREATE"

    # Check audit log
    audits = db.query(AuditLog).filter(AuditLog.entity_id == question.id).all()
    assert len(audits) == 1
    assert audits[0].action == "question.create"

    # Verify it's a CMSQuestion
    assert isinstance(question, CMSQuestion)


def test_submit_validation_fails_missing_fields(db: Session, admin_user: User):
    """Test that submit validation fails when required fields are missing."""
    # Create question without required fields
    question_data = QuestionCreate(
        stem="Test question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        option_e="E",
        correct_index=0,
        # Missing: year_id, block_id, theme_id, difficulty, cognitive_level
    )
    question = create_question(db, question_data, admin_user.id)

    # Try to submit - should fail
    with pytest.raises(QuestionWorkflowError) as exc_info:
        submit_question(db, question.id, admin_user)
    assert (
        "year_id" in str(exc_info.value.detail) or "required" in str(exc_info.value.detail).lower()
    )


def test_submit_success(db: Session, admin_user: User, sample_question_data: QuestionCreate):
    """Test successful question submission."""
    question = create_question(db, sample_question_data, admin_user.id)

    # Submit
    question = submit_question(db, question.id, admin_user)

    assert question.status == QuestionStatus.IN_REVIEW

    # Check version was created
    versions = db.query(QuestionVersion).filter(QuestionVersion.question_id == question.id).all()
    assert len(versions) == 2  # CREATE + STATUS_CHANGE
    assert versions[1].change_kind.value == "STATUS_CHANGE"

    # Check audit log
    audits = db.query(AuditLog).filter(AuditLog.entity_id == question.id).all()
    assert len(audits) >= 2
    submit_audit = next((a for a in audits if a.action == "question.submit"), None)
    assert submit_audit is not None


def test_reviewer_cannot_publish(
    db: Session, reviewer_user: User, sample_question_data: QuestionCreate
):
    """Test that reviewer cannot publish questions."""
    question = create_question(db, sample_question_data, reviewer_user.id)
    question = submit_question(db, question.id, reviewer_user)
    question = approve_question(db, question.id, reviewer_user)

    # Reviewer should not be able to publish
    with pytest.raises(QuestionWorkflowError) as exc_info:
        publish_question(db, question.id, reviewer_user)
    assert "ADMIN" in str(exc_info.value.detail) or "publish" in str(exc_info.value.detail).lower()


def test_publish_requires_source(
    db: Session, admin_user: User, sample_question_data: QuestionCreate
):
    """Test that publishing requires source_book and source_page."""
    question = create_question(db, sample_question_data, admin_user.id)
    question = submit_question(db, question.id, admin_user)
    question = approve_question(db, question.id, admin_user)

    # Try to publish without source - should fail
    with pytest.raises(QuestionWorkflowError) as exc_info:
        publish_question(db, question.id, admin_user)
    assert "source" in str(exc_info.value.detail).lower()

    # Add source and publish
    question.source_book = "Test Book"
    question.source_page = "p. 42"
    db.commit()

    question = publish_question(db, question.id, admin_user)
    assert question.status == QuestionStatus.PUBLISHED
    assert question.published_at is not None


def test_status_transition_invalid(
    db: Session, admin_user: User, sample_question_data: QuestionCreate
):
    """Test that invalid status transitions are rejected."""
    question = create_question(db, sample_question_data, admin_user.id)

    # Try to approve a DRAFT question directly (should fail - must submit first)
    with pytest.raises(QuestionWorkflowError):
        approve_question(db, question.id, admin_user)


def test_version_created_on_edit_and_status_change(
    db: Session, admin_user: User, sample_question_data: QuestionCreate
):
    """Test that versions are created on edits and status changes."""
    question = create_question(db, sample_question_data, admin_user.id)

    # Initial version (CREATE)
    versions = db.query(QuestionVersion).filter(QuestionVersion.question_id == question.id).all()
    assert len(versions) == 1

    # Edit question
    from app.schemas.question_cms import QuestionUpdate
    from app.services.question_cms import update_question

    update_data = QuestionUpdate(stem="Updated stem")
    question = update_question(db, question.id, update_data, admin_user.id)

    # Should have 2 versions now (CREATE + EDIT)
    versions = db.query(QuestionVersion).filter(QuestionVersion.question_id == question.id).all()
    assert len(versions) == 2
    assert versions[1].change_kind.value == "EDIT"

    # Submit (status change)
    question = submit_question(db, question.id, admin_user)
    versions = db.query(QuestionVersion).filter(QuestionVersion.question_id == question.id).all()
    assert len(versions) == 3
    assert versions[2].change_kind.value == "STATUS_CHANGE"


def test_audit_log_written_on_create_update_publish(
    db: Session, admin_user: User, sample_question_data: QuestionCreate
):
    """Test that audit logs are written for all actions."""
    question = create_question(db, sample_question_data, admin_user.id)

    # Check create audit
    audits = db.query(AuditLog).filter(AuditLog.entity_id == question.id).all()
    assert len(audits) == 1
    assert audits[0].action == "question.create"

    # Update
    from app.schemas.question_cms import QuestionUpdate
    from app.services.question_cms import update_question

    update_data = QuestionUpdate(stem="Updated")
    question = update_question(db, question.id, update_data, admin_user.id)

    audits = db.query(AuditLog).filter(AuditLog.entity_id == question.id).all()
    assert len(audits) == 2
    assert any(a.action == "question.update" for a in audits)

    # Add source and publish
    question.source_book = "Book"
    question.source_page = "p. 1"
    question = submit_question(db, question.id, admin_user)
    question = approve_question(db, question.id, admin_user)
    question = publish_question(db, question.id, admin_user)

    audits = db.query(AuditLog).filter(AuditLog.entity_id == question.id).all()
    assert len(audits) >= 5  # create, update, submit, approve, publish
    assert any(a.action == "question.publish" for a in audits)
