import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import asyncpg

logger = logging.getLogger(__name__)

async def get_active_cache(conn: asyncpg.Connection, cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve active, unexpired Gemini cache session metadata matching the cache_key.
    """
    query = """
        SELECT id, cache_key, google_cache_name, expires_at
        FROM gemini_cache_registry
        WHERE cache_key = $1 AND expires_at > $2
        LIMIT 1
    """
    now = datetime.now(timezone.utc)
    row = await conn.fetchrow(query, cache_key, now)
    if row:
        logger.info(f"[CacheRegistry] Hit active cache: key={cache_key[:8]}, name={row['google_cache_name']}")
        return dict(row)
    return None

async def register_cache(
    conn: asyncpg.Connection, 
    cache_key: str, 
    google_cache_name: str, 
    expires_at: datetime
) -> Dict[str, Any]:
    """
    Insert or update a Gemini cache session in the registry.
    """
    # Enforce UTC timezone
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = expires_at.astimezone(timezone.utc)

    query = """
        INSERT INTO gemini_cache_registry (cache_key, google_cache_name, expires_at)
        VALUES ($1, $2, $3)
        ON CONFLICT (cache_key) 
        DO UPDATE SET google_cache_name = EXCLUDED.google_cache_name, expires_at = EXCLUDED.expires_at
        RETURNING id, cache_key, google_cache_name, expires_at
    """
    row = await conn.fetchrow(query, cache_key, google_cache_name, expires_at)
    logger.info(f"[CacheRegistry] Registered/Updated cache: key={cache_key[:8]}, name={google_cache_name}")
    return dict(row) if row else {}
