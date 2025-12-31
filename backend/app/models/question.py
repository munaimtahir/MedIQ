"""Question model."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Question(Base):
    """Question model."""

    __tablename__ = "questions"

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

    theme = relationship("Theme", back_populates="questions")

