from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    role = Column(String, nullable=False)  # "student" or "admin"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Block(Base):
    __tablename__ = "blocks"

    id = Column(String, primary_key=True)  # "A", "B", "C", etc.
    name = Column(String, nullable=False)
    year = Column(Integer, nullable=False)  # 1 or 2
    description = Column(Text)

    themes = relationship("Theme", back_populates="block")


class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    block_id = Column(String, ForeignKey("blocks.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)

    block = relationship("Block", back_populates="themes")
    questions = relationship("Question", back_populates="theme")


class Question(Base):
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


class AttemptSession(Base):
    __tablename__ = "attempt_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    question_count = Column(Integer, nullable=False)
    time_limit_minutes = Column(Integer, nullable=False)
    question_ids = Column(JSON)  # List of question IDs
    is_submitted = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True))

    answers = relationship("AttemptAnswer", back_populates="session")


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("attempt_sessions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    selected_option_index = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    is_marked_for_review = Column(Boolean, default=False)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("AttemptSession", back_populates="answers")
