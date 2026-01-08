"""Attempt models (Session and Answer)."""

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AttemptSession(Base):
    """Attempt session model."""

    __tablename__ = "attempt_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    question_count = Column(Integer, nullable=False)
    time_limit_minutes = Column(Integer, nullable=False)
    question_ids = Column(JSON)  # List of question IDs
    is_submitted = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True))

    answers = relationship("AttemptAnswer", back_populates="session")


class AttemptAnswer(Base):
    """Attempt answer model."""

    __tablename__ = "attempt_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("attempt_sessions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    selected_option_index = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    is_marked_for_review = Column(Boolean, default=False)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("AttemptSession", back_populates="answers")
