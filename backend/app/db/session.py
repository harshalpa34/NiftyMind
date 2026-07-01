"""
Async session factory and database dependency for FastAPI.
"""
import logging
from typing import AsyncGenerator
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.db.base import get_engine

logger = logging.getLogger(__name__)

# Module-level session factory
import asyncpg
from app.config import get_settings

logger = logging.getLogger(__name__)

# Module-level session factory
AsyncSessionFactory: async_sessionmaker | None = None

# Global asyncpg connection pool for raw SQL queries
pg_pool: asyncpg.Pool | None = None


def get_session_factory() -> async_sessionmaker:
    """
    Get or create the async session factory.
    
    Returns:
        async_sessionmaker: Factory for creating async sessions.
    """
    global AsyncSessionFactory
    
    if AsyncSessionFactory is None:
        AsyncSessionFactory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("Async session factory initialized")
    
    return AsyncSessionFactory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting an async database session.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_pg_pool():
    """Initialize the raw connection pool (asyncpg) for SQL queries."""
    global pg_pool
    if pg_pool is not None:
        return
        
    settings = get_settings()
    if not settings.database_url:
        logger.warning("DATABASE_URL not set. Raw pg_pool cannot be initialized.")
        return

    # Convert url scheme from postgresql+asyncpg to postgresql
    pg_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        pg_pool = await asyncpg.create_pool(pg_url, min_size=1, max_size=3)
        logger.info("✓ Raw asyncpg PostgreSQL connection pool initialized")
    except Exception as exc:
        logger.warning(f"Could not connect raw pg_pool: {exc} (Application will start, but database endpoints will be unavailable).")


async def close_pg_pool():
    """Close the raw postgresql connection pool on shutdown."""
    global pg_pool
    if pg_pool:
        await pg_pool.close()
        pg_pool = None
        logger.info("✓ Raw asyncpg pool closed")


async def get_raw_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    FastAPI dependency to yield a raw asyncpg Connection.
    Bypasses SQLAlchemy entirely.
    """
    global pg_pool
    if pg_pool is None:
        await init_pg_pool()
        if pg_pool is None:
            raise HTTPException(
                status_code=503,
                detail="Database connection is unavailable."
            )
            
    async with pg_pool.acquire() as conn:
        yield conn
