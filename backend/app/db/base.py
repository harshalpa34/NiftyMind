"""
Database engine configuration and initialization.
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

logger = logging.getLogger(__name__)

# Module-level engine instance
engine: AsyncEngine | None = None


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def create_engine() -> AsyncEngine:
    """
    Create an async PostgreSQL engine with connection pooling.
    
    Returns:
        AsyncEngine: Configured async engine instance.
        
    Raises:
        ValueError: If database_url is not configured.
    """
    settings = get_settings()
    
    if not settings.database_url:
        raise ValueError("DATABASE_URL is not configured in environment variables")
    
    # Extract host for logging (hide credentials)
    try:
        # postgresql+asyncpg://user:pass@host:port/dbname
        url_parts = settings.database_url.split("://")[1].split("/")[0].split("@")
        host = url_parts[-1].split(":")[0] if len(url_parts) > 0 else "unknown"
    except (IndexError, AttributeError):
        host = "unknown"
    
    engine_instance = create_async_engine(
        settings.database_url,
        pool_size=3,
        max_overflow=2,
        pool_pre_ping=True,
        echo=settings.debug,
    )
    
    logger.info(
        f"Async PostgreSQL engine created: host={host}, pool_size=3, max_overflow=2"
    )
    
    return engine_instance


def get_engine() -> AsyncEngine:
    """
    Get or create the async database engine.
    
    Returns:
        AsyncEngine: The module-level engine instance.
    """
    global engine
    
    if engine is None:
        engine = create_engine()
    
    return engine
