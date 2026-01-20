"""Syllabus models (Year, Block, and Theme)."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Year(Base):
    """Year model (e.g., 1st Year, 2nd Year, Final Year)."""

    __tablename__ = "years"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    order_no = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    blocks = relationship("Block", back_populates="year", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("name", name="uq_year_name"),)


class Block(Base):
    """Block model (e.g., Block A, Block B)."""

    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year_id = Column(Integer, ForeignKey("years.id", onupdate="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)  # e.g., "A", "B", "C"
    name = Column(String(100), nullable=False)  # e.g., "Block A"
    order_no = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    year = relationship("Year", back_populates="blocks")
    themes = relationship("Theme", back_populates="block", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("year_id", "code", name="uq_block_year_code"),)


class Theme(Base):
    """Theme model."""

    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    block_id = Column(Integer, ForeignKey("blocks.id", onupdate="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    order_no = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    block = relationship("Block", back_populates="themes")
    # Note: CMS questions use Question model from question_cms.py, not legacy Question

    __table_args__ = (UniqueConstraint("block_id", "title", name="uq_theme_block_title"),)
