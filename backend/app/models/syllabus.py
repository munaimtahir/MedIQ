"""Syllabus models (Block and Theme)."""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Block(Base):
    """Block model."""

    __tablename__ = "blocks"

    id = Column(String, primary_key=True)  # "A", "B", "C", etc.
    name = Column(String, nullable=False)
    year = Column(Integer, nullable=False)  # 1 or 2
    description = Column(Text)

    themes = relationship("Theme", back_populates="block")


class Theme(Base):
    """Theme model."""

    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    block_id = Column(String, ForeignKey("blocks.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)

    block = relationship("Block", back_populates="themes")
    questions = relationship("Question", back_populates="theme")

