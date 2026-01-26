"""Build Elasticsearch documents from question data."""

import re
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.question_cms import Question, QuestionStatus, QuestionVersion
from app.models.syllabus import Block, Theme, Year


def strip_markdown(text: str | None) -> str:
    """
    Strip markdown syntax from text (simple regex-based approach).

    Args:
        text: Markdown text

    Returns:
        Plain text
    """
    if not text:
        return ""
    
    # Remove markdown headers
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    # Remove links
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove code blocks
    text = re.sub(r"```[^`]*```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove images
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", text)
    # Remove horizontal rules
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    # Remove list markers
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Clean up extra whitespace
    text = re.sub(r"\n\s*\n", "\n", text)
    text = text.strip()
    
    return text


def build_question_document(
    db: Session,
    question: Question,
    version: QuestionVersion | None = None,
) -> dict[str, Any] | None:
    """
    Build Elasticsearch document from question and version.

    Args:
        db: Database session
        question: Question model
        version: Optional version (if None, uses latest published version)

    Returns:
        Document dict or None if question is not published
    """
    # Only index published questions
    if question.status != QuestionStatus.PUBLISHED:
        return None

    # Get version if not provided
    if version is None:
        version = (
            db.query(QuestionVersion)
            .filter(QuestionVersion.question_id == question.id)
            .order_by(QuestionVersion.version_no.desc())
            .first()
        )
        if not version:
            return None

    # Build options array
    options = []
    if question.option_a:
        options.append(question.option_a)
    if question.option_b:
        options.append(question.option_b)
    if question.option_c:
        options.append(question.option_c)
    if question.option_d:
        options.append(question.option_d)
    if question.option_e:
        options.append(question.option_e)

    # Get syllabus names
    block_name = None
    theme_name = None
    topic_name = None
    year = None

    if question.block_id:
        block = db.query(Block).filter(Block.id == question.block_id).first()
        if block:
            block_name = block.name
            if block.year_id:
                year_obj = db.query(Year).filter(Year.id == block.year_id).first()
                if year_obj:
                    year = year_obj.order_no  # Use order_no as year number

    if question.theme_id:
        theme = db.query(Theme).filter(Theme.id == question.theme_id).first()
        if theme:
            theme_name = theme.title

    # Extract concept_ids (if stored as array in snapshot or separate table)
    concept_ids = []
    if question.concept_id:
        concept_ids.append(str(question.concept_id))

    # Extract source_page as integer if possible
    source_page_int = None
    if question.source_page:
        # Try to extract number from "p. 12-13" or "12" or "12-13"
        match = re.search(r"(\d+)", question.source_page)
        if match:
            try:
                source_page_int = int(match.group(1))
            except ValueError:
                pass

    # Build tags_text (combine tags if available)
    tags_text = ""
    # TODO: If tags are stored separately, fetch and combine them
    # For now, we'll leave it empty or extract from snapshot if available

    # Build document
    doc: dict[str, Any] = {
        "question_id": str(question.id),
        "version_id": str(version.id),
        "status": question.status.value,
        "published_at": question.published_at.isoformat() if question.published_at else None,
        "updated_at": question.updated_at.isoformat() if question.updated_at else None,
        "is_active": question.status == QuestionStatus.PUBLISHED,
        # Syllabus
        "year": year,
        "block_id": str(question.block_id) if question.block_id else None,
        "block_name": block_name,
        "theme_id": str(question.theme_id) if question.theme_id else None,
        "theme_name": theme_name,
        "topic_id": str(question.topic_id) if question.topic_id else None,
        "topic_name": topic_name,
        "concept_ids": concept_ids,
        # Pedagogy
        "cognitive_level": question.cognitive_level,
        "difficulty_label": question.difficulty,
        "source_book": question.source_book,
        "source_page": source_page_int,
        "source_ref": question.source_ref,
        # Content
        "stem": question.stem or "",
        "options": options,
        "explanation_md": question.explanation_md or "",
        "explanation_plain": strip_markdown(question.explanation_md),
        "tags_text": tags_text,
    }

    # Remove None values for cleaner indexing
    doc = {k: v for k, v in doc.items() if v is not None}

    return doc
