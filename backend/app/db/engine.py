"""Database engine configuration."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import settings


def create_db_engine() -> Engine:
    """Create SQLAlchemy engine."""
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10,
        echo=False,  # Set to True for SQL query logging
    )


# Global engine instance
engine = create_db_engine()

