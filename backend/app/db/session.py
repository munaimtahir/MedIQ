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
        # Convert postgresql:// to postgresql+asyncpg:// for async
        async_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        _async_engine = create_async_engine(
            async_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=10,
            pool_timeout=30,
            echo=False,
        )
        _AsyncSessionLocal = async_sessionmaker(
            _async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async with _AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
