"""Versioning helpers for question snapshots."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.question_cms import ChangeKind, Question, QuestionVersion


def snapshot_question(question: Question) -> dict[str, Any]:
    """Create a snapshot of question fields for versioning."""
    return {
        "id": str(question.id),
        "stem": question.stem,
        "option_a": question.option_a,
        "option_b": question.option_b,
        "option_c": question.option_c,
        "option_d": question.option_d,
        "option_e": question.option_e,
        "correct_index": question.correct_index,
        "explanation_md": question.explanation_md,
        "status": question.status.value if question.status else None,
        "year_id": question.year_id,
        "block_id": question.block_id,
        "theme_id": question.theme_id,
        "topic_id": question.topic_id,
        "concept_id": question.concept_id,
        "cognitive_level": question.cognitive_level,
        "difficulty": question.difficulty,
        "source_book": question.source_book,
        "source_page": question.source_page,
        "source_ref": question.source_ref,
        "created_by": str(question.created_by) if question.created_by else None,
        "updated_by": str(question.updated_by) if question.updated_by else None,
        "approved_by": str(question.approved_by) if question.approved_by else None,
        "approved_at": question.approved_at.isoformat() if question.approved_at else None,
        "published_at": question.published_at.isoformat() if question.published_at else None,
        "created_at": question.created_at.isoformat() if question.created_at else None,
        "updated_at": question.updated_at.isoformat() if question.updated_at else None,
    }


def create_version(
    db: Session,
    question_id: UUID,
    change_kind: ChangeKind,
    changed_by: UUID,
    snapshot: dict[str, Any],
    change_reason: str | None = None,
) -> QuestionVersion:
    """Create a new version snapshot for a question."""
    # Get current max version number
    max_version = (
        db.query(QuestionVersion.version_no)
        .filter(QuestionVersion.question_id == question_id)
        .order_by(QuestionVersion.version_no.desc())
        .first()
    )
    next_version = (max_version[0] if max_version else 0) + 1

    version = QuestionVersion(
        question_id=question_id,
        version_no=next_version,
        snapshot=snapshot,
        change_kind=change_kind,
        change_reason=change_reason,
        changed_by=changed_by,
    )
    db.add(version)
    return version
