import pytest
import asyncpg
import sqlalchemy.ext.asyncio

# Monkeypatch asyncpg and SQLAlchemy before importing app to limit database connections
original_create_pool = asyncpg.create_pool
async def patched_create_pool(*args, **kwargs):
    kwargs["min_size"] = 1
    kwargs["max_size"] = 1
    return await original_create_pool(*args, **kwargs)
asyncpg.create_pool = patched_create_pool

original_create_async_engine = sqlalchemy.ext.asyncio.create_async_engine
def patched_create_async_engine(*args, **kwargs):
    kwargs["pool_size"] = 1
    kwargs["max_overflow"] = 0
    return original_create_async_engine(*args, **kwargs)
sqlalchemy.ext.asyncio.create_async_engine = patched_create_async_engine

from httpx import ASGITransport, AsyncClient
from main import app
from app.db.session import pg_pool

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    # Lifespan will run startup (initializing pg_pool, etc.) and shutdown (closing pg_pool)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

@pytest.fixture
async def db_conn(client):
    import app.db.session
    async with app.db.session.pg_pool.acquire() as conn:
        yield conn


@pytest.fixture(autouse=True)
async def clean_database():
    # Execute the test first
    yield
    
    # Clean up test users created during the test.
    # Due to foreign keys ON DELETE CASCADE, this automatically deletes all related
    # portfolios, holdings, portfolio_transactions, and user_sessions.
    import app.db.session
    if app.db.session.pg_pool:
        async with app.db.session.pg_pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE email LIKE 'testuser_%'")


@pytest.fixture(autouse=True)
def mock_stock_price_fetching():
    from unittest.mock import patch
    from app.services.portfolio_risk import MOCK_MARKET_PRICES
    
    async def mock_fetch(client, symbol):
        return MOCK_MARKET_PRICES.get(symbol.upper())

    with patch("app.db.crud.portfolio._fetch_stock_price_internal", side_effect=mock_fetch):
        yield
