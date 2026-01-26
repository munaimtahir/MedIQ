"""Database engine configuration."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.db.instrumentation import instrument_engine


def create_db_engine() -> Engine:
    """Create SQLAlchemy engine with production-hardened pool settings."""
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using (reconnect on stale)
        pool_size=10,  # Base pool size (increased from 5 for exam-time load)
        max_overflow=10,  # Additional connections beyond pool_size
        pool_timeout=30,  # Seconds to wait for connection from pool
        echo=False,  # Set to True for SQL query logging
    )
    # Attach performance instrumentation (slow SQL logging + counters)
    instrument_engine(engine)
    return engine


# Global engine instance
engine = create_db_engine()
