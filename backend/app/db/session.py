"""Database session management."""

from collections.abc import AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.engine import engine

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Prevent lazy loading issues
)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Async session factory for endpoints that need async operations
_async_engine = None
_AsyncSessionLocal = None


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    global _async_engine, _AsyncSessionLocal
    
    if _async_engine is None:
        # Convert postgresql:// or postgresql+psycopg2:// to postgresql+asyncpg:// for async
        async_url = settings.DATABASE_URL
        if not async_url:
            raise ValueError("DATABASE_URL is not set")
        
        # Validate that we have a database name in the URL
        from urllib.parse import urlparse
        parsed = urlparse(async_url.replace("postgresql+psycopg2://", "postgresql://", 1).replace("postgresql+asyncpg://", "postgresql://", 1))
        if not parsed.path or len(parsed.path) <= 1:
            raise ValueError(
                f"Invalid DATABASE_URL: missing database name. "
                f"Expected format: postgresql[+driver]://user:password@host:port/database_name. "
                f"Got: {async_url[:80]}..."
            )
        
        database_name = parsed.path.lstrip("/")
        if not database_name:
            raise ValueError(
                f"Invalid DATABASE_URL: database name is empty. "
                f"URL: {async_url[:80]}..."
            )
        
        # Convert to async format
        if "postgresql+psycopg2://" in async_url:
            async_url = async_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        elif "postgresql://" in async_url:
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        _async_engine = create_async_engine(
            async_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=10,
            pool_timeout=30,
            echo=False,
            connect_args={
                "connect_timeout": 10,  # Connection timeout in seconds
            },
        )
        _AsyncSessionLocal = async_sessionmaker(
            _async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    if _AsyncSessionLocal is None:
        raise RuntimeError("Async session factory not initialized")
    
    async with _AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
