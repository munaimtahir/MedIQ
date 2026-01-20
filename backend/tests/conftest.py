"""Pytest configuration and shared fixtures."""

import os
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.question_cms import Question as CMSQuestion
from app.models.syllabus import Block, Theme, Year
from app.models.user import User

# Use test database URL if available, otherwise use PostgreSQL from env
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://exam_user:change_me@localhost:5432/exam_platform"),
)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a test database session with transaction rollback."""
    from app.db.session import SessionLocal

    # Use the actual database but wrap in transaction that rolls back
    session = SessionLocal()

    # Start a transaction
    trans = session.begin()

    try:
        # Ensure test data exists (year, block, theme)
        year = session.query(Year).filter(Year.id == 1).first()
        if not year:
            year = Year(id=1, name="1st Year", order_no=1, is_active=True)
            session.add(year)
            session.flush()

        block = session.query(Block).filter(Block.id == 1).first()
        if not block:
            block = Block(id=1, year_id=1, code="A", name="Test Block", order_no=1, is_active=True)
            session.add(block)
            session.flush()

        theme = session.query(Theme).filter(Theme.id == 1).first()
        if not theme:
            theme = Theme(id=1, block_id=1, title="Test Theme", order_no=1, is_active=True)
            session.add(theme)
            session.flush()

        yield session
    finally:
        # Rollback transaction to clean up test data
        trans.rollback()
        session.close()
