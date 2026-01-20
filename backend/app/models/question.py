"""Question model."""

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class QuestionLegacy(Base):
    """Question model (legacy - use CMSQuestion for new questions)."""

    __tablename__ = "questions_legacy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # List of 5 strings
    correct_option_index = Column(Integer, nullable=False)  # 0-4
    explanation = Column(Text)
    tags = Column(JSON)  # List of strings
    difficulty = Column(String)  # "easy", "medium", "hard"
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Legacy relationship - disabled since Theme no longer has questions relationship
    # theme = relationship("Theme", back_populates="questions")
