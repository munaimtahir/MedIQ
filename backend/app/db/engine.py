"""Database engine configuration."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from urllib.parse import urlparse

from app.core.config import settings
from app.db.instrumentation import instrument_engine


def create_db_engine() -> Engine:
    """Create SQLAlchemy engine with production-hardened pool settings."""
    # Validate connection string format
    db_url = settings.DATABASE_URL
    if not db_url:
        raise ValueError("DATABASE_URL is not set")
    
    # Parse and validate the connection string
    try:
        # Parse the URL to extract components
        # Handle both postgresql:// and postgresql+psycopg2:// formats
        parsed = urlparse(db_url.replace("postgresql+psycopg2://", "postgresql://", 1))
        
        # Ensure we have a database name (path should be /database_name)
        if not parsed.path or len(parsed.path) <= 1:
            raise ValueError(
                f"Invalid DATABASE_URL: missing database name. "
                f"Expected format: postgresql[+driver]://user:password@host:port/database_name. "
                f"Got: {db_url[:80]}..."
            )
        
        # Extract database name (remove leading /)
        database_name = parsed.path.lstrip("/")
        if not database_name:
            raise ValueError(
                f"Invalid DATABASE_URL: database name is empty. "
                f"URL: {db_url[:80]}..."
            )
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to parse DATABASE_URL: {e}. URL: {db_url[:80]}...") from e
    
    engine = create_engine(
        db_url,
        pool_pre_ping=True,  # Verify connections before using (reconnect on stale)
        pool_size=10,  # Base pool size (increased from 5 for exam-time load)
        max_overflow=10,  # Additional connections beyond pool_size
        pool_timeout=30,  # Seconds to wait for connection from pool
        echo=False,  # Set to True for SQL query logging
        connect_args={
            # Add connection arguments to ensure proper database connection
            "connect_timeout": 10,  # Connection timeout in seconds
        },
    )
    # Attach performance instrumentation (slow SQL logging + counters)
    instrument_engine(engine)
    return engine


# Global engine instance
# Note: Engine creation is lazy - SQLAlchemy doesn't connect until first use
# but we create the engine object here for dependency injection
engine = create_db_engine()
