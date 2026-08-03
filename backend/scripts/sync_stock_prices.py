import os
import sys
import asyncio
import logging
from typing import Set, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("stock_prices_syncer")

# Add backend directory to sys.path so we can import app modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Load environment variables from the backend/.env file
from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

import app.db.session as db_session
import httpx

async def resolve_yahoo_symbol(client: httpx.AsyncClient, db_symbol: str) -> str:
    """Dynamically resolve the Yahoo Finance symbol using its search API."""
    cleaned = db_symbol.strip().upper()
    
    # 1. If it's already a short string with no spaces, it is likely already a ticker (e.g. INFY, TCS)
    if len(cleaned) <= 10 and " " not in cleaned:
        if cleaned.endswith(".NS") or cleaned.endswith(".BO"):
            return cleaned

    # 2. Query Yahoo Finance Search API
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={cleaned}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = await client.get(url, headers=headers, timeout=5.0)
        if response.status_code == 200:
            quotes = response.json().get("quotes", [])
            for q in quotes:
                symbol = q.get("symbol", "")
                # Prioritize NSE (.NS) and fallback to BSE (.BO)
                if symbol.endswith(".NS") or symbol.endswith(".BO"):
                    logger.info(f"Resolved symbol '{db_symbol}' to ticker '{symbol}' via Yahoo Search API")
                    return symbol
    except Exception as e:
        logger.warning(f"Failed to dynamically search ticker for '{db_symbol}': {e}")
        
    # 3. Fallback to original symbol if lookup fails
    return cleaned

async def get_holdings_tickers() -> Set[str]:
    """Fetch unique ticker symbols from active holdings database."""
    logger.info("Initializing raw database pool to fetch tickers...")
    await db_session.init_pg_pool()
    
    if db_session.pg_pool is None:
        logger.error("Failed to initialize database pool.")
        return set()
        
    try:
        async with db_session.pg_pool.acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT symbol FROM holdings;")
            tickers = {row["symbol"].strip().upper() for row in rows if row["symbol"]}
            logger.info(f"Retrieved active holdings tickers from database: {tickers}")
            return tickers
    except Exception as e:
        logger.error(f"Error querying holdings database: {e}")
        return set()

async def fetch_stock_price(client: httpx.AsyncClient, db_symbol: str) -> float | None:
    """Fetch current price for a symbol from Yahoo Finance API using dynamic ticker resolution."""
    yahoo_ticker = await resolve_yahoo_symbol(client, db_symbol)
    
    if not (yahoo_ticker.endswith(".NS") or yahoo_ticker.endswith(".BO")):
        ticker_to_query = f"{yahoo_ticker}.NS"
    else:
        ticker_to_query = yahoo_ticker

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_to_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    logger.info(f"Fetching price for {db_symbol} (using ticker: {yahoo_ticker}) from Yahoo Finance...")
    try:
        response = await client.get(url, headers=headers, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            if price is not None:
                logger.info(f"✓ {db_symbol}: ₹{price}")
                return float(price)
            logger.error(f"✗ No price data found in metadata for {db_symbol} ({yahoo_ticker})")
        else:
            logger.error(f"✗ Failed to fetch price for {db_symbol} ({yahoo_ticker}): HTTP status {response.status_code}")
    except Exception as e:
        logger.error(f"✗ Error fetching price for {db_symbol} ({yahoo_ticker}): {e}")
    return None

async def sync_prices():
    tickers = await get_holdings_tickers()
    if not tickers:
        logger.info("No active holdings found in database. Nothing to sync.")
        await db_session.close_pg_pool()
        return

    # Fetch prices concurrently using a shared client session
    logger.info(f"Fetching market prices for {len(tickers)} symbols...")
    async with httpx.AsyncClient() as client:
        tasks = {ticker: fetch_stock_price(client, ticker) for ticker in tickers}
        results = await asyncio.gather(*tasks.values())
        
        ticker_prices: Dict[str, float] = {}
        for ticker, price in zip(tasks.keys(), results):
            if price is not None:
                ticker_prices[ticker] = price

    if not ticker_prices:
        logger.warning("No prices were successfully fetched. Aborting database upsert.")
        await db_session.close_pg_pool()
        return

    # Upsert prices into database (using original db_symbol)
    logger.info("Upserting current stock prices into database...")
    try:
        async with db_session.pg_pool.acquire() as conn:
            # We execute in a single transaction for efficiency
            async with conn.transaction():
                for ticker, price in ticker_prices.items():
                    await conn.execute("""
                        INSERT INTO stock_prices (symbol, price, updated_at)
                        VALUES ($1, $2, CURRENT_TIMESTAMP)
                        ON CONFLICT (symbol)
                        DO UPDATE SET price = EXCLUDED.price, updated_at = CURRENT_TIMESTAMP;
                    """, ticker, price)
        logger.info(f"✓ Successfully synced {len(ticker_prices)} stock prices!")
    except Exception as e:
        logger.error(f"Failed to upsert stock prices: {e}")
    finally:
        await db_session.close_pg_pool()

if __name__ == "__main__":
    asyncio.run(sync_prices())
