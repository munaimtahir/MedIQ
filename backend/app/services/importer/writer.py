"""Writer for import engine - bulk insert questions."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.question_cms import Question, QuestionStatus


class QuestionWriter:
    """Write validated questions to database."""

    def __init__(self, db: Session, created_by: UUID):
        """
        Initialize writer.

        Args:
            db: Database session
            created_by: User ID creating questions
        """
        self.db = db
        self.created_by = created_by

    def bulk_insert(self, questions_data: list[dict[str, Any]]) -> int:
        """
        Bulk insert questions as DRAFT.

        Args:
            questions_data: List of validated canonical question dicts

        Returns:
            Number of questions inserted
        """
        if not questions_data:
            return 0

        questions = []
        for data in questions_data:
            question = Question(
                external_id=data.get("external_id"),
                stem=data.get("stem"),
                option_a=data.get("option_a"),
                option_b=data.get("option_b"),
                option_c=data.get("option_c"),
                option_d=data.get("option_d"),
                option_e=data.get("option_e"),
                correct_index=data.get("correct"),  # Already converted to 0-4
                explanation_md=data.get("explanation_md"),
                year_id=data.get("year_id"),
                block_id=data.get("block_id"),
                theme_id=data.get("theme_id"),
                topic_id=data.get("topic_id"),
                concept_id=data.get("concept_id"),
                cognitive_level=data.get("cognitive"),
                difficulty=data.get("difficulty"),
                source_book=data.get("source_book"),
                source_page=str(data.get("source_page")) if data.get("source_page") else None,
                source_ref=data.get("source_ref"),
                status=QuestionStatus.DRAFT,
                created_by=self.created_by,
                updated_by=self.created_by,
            )
            questions.append(question)

        # Bulk insert
        self.db.bulk_save_objects(questions)
        self.db.flush()

        return len(questions)
