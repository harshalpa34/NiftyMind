import uuid
import logging
from typing import Optional, List, Dict, Any
import asyncpg

logger = logging.getLogger(__name__)

# ============================================================================
# Portfolio CRUD
# ============================================================================

async def create_portfolio(conn: asyncpg.Connection, name: str, user_id: uuid.UUID) -> Dict[str, Any]:
    """Create a new portfolio for a user using raw SQL with asyncpg."""
    portfolio_id = uuid.uuid4()
    query = """
        INSERT INTO portfolios (id, user_id, name)
        VALUES ($1, $2, $3)
        RETURNING id, user_id, name, created_at, updated_at
    """
    row = await conn.fetchrow(query, portfolio_id, user_id, name)
    logger.info("Portfolio created via raw asyncpg SQL", extra={"portfolio_id": str(portfolio_id), "user_id": str(user_id)})
    return dict(row) if row else {}

async def get_portfolios(conn: asyncpg.Connection, user_id: uuid.UUID) -> List[Dict[str, Any]]:
    """List all portfolios for a user using raw SQL with asyncpg."""
    query = """
        SELECT id, user_id, name, created_at, updated_at
        FROM portfolios
        WHERE user_id = $1
        ORDER BY created_at DESC
    """
    rows = await conn.fetch(query, user_id)
    return [dict(row) for row in rows]

async def get_portfolio(conn: asyncpg.Connection, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """Retrieve a specific portfolio for a user using raw SQL with asyncpg."""
    query = """
        SELECT id, user_id, name, created_at, updated_at
        FROM portfolios
        WHERE id = $1 AND user_id = $2
    """
    row = await conn.fetchrow(query, portfolio_id, user_id)
    return dict(row) if row else None

async def delete_portfolio(conn: asyncpg.Connection, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Delete a specific portfolio for a user using raw SQL with asyncpg."""
    query = """
        DELETE FROM portfolios
        WHERE id = $1 AND user_id = $2
    """
    result = await conn.execute(query, portfolio_id, user_id)
    return "DELETE 1" in result or " 1" in result

# ============================================================================
# Holdings CRUD
# ============================================================================

async def get_holdings(conn: asyncpg.Connection, portfolio_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Retrieve all holdings for a portfolio using raw SQL with asyncpg."""
    query = """
        SELECT id, portfolio_id, symbol, quantity, average_buy_price, created_at, updated_at
        FROM holdings
        WHERE portfolio_id = $1
        ORDER BY symbol ASC
    """
    rows = await conn.fetch(query, portfolio_id)
    return [dict(row) for row in rows]

async def get_holding(conn: asyncpg.Connection, portfolio_id: uuid.UUID, symbol: str) -> Optional[Dict[str, Any]]:
    """Retrieve a specific holding by symbol for a portfolio using raw SQL with asyncpg."""
    query = """
        SELECT id, portfolio_id, symbol, quantity, average_buy_price, created_at, updated_at
        FROM holdings
        WHERE portfolio_id = $1 AND UPPER(symbol) = UPPER($2)
    """
    row = await conn.fetchrow(query, portfolio_id, symbol)
    return dict(row) if row else None

async def upsert_holding(
    conn: asyncpg.Connection, 
    portfolio_id: uuid.UUID, 
    symbol: str, 
    quantity: float, 
    average_buy_price: float
) -> Dict[str, Any]:
    """Upsert a holding record directly using raw SQL with asyncpg."""
    holding_id = uuid.uuid4()
    query = """
        INSERT INTO holdings (id, portfolio_id, symbol, quantity, average_buy_price)
        VALUES ($1, $2, UPPER($3), $4, $5)
        ON CONFLICT (portfolio_id, symbol)
        DO UPDATE SET 
            quantity = EXCLUDED.quantity,
            average_buy_price = EXCLUDED.average_buy_price,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id, portfolio_id, symbol, quantity, average_buy_price, created_at, updated_at
    """
    row = await conn.fetchrow(query, holding_id, portfolio_id, symbol, quantity, average_buy_price)
    return dict(row) if row else {}

async def delete_holding(conn: asyncpg.Connection, portfolio_id: uuid.UUID, symbol: str) -> bool:
    """Delete a holding record from the portfolio using raw SQL with asyncpg."""
    query = """
        DELETE FROM holdings
        WHERE portfolio_id = $1 AND UPPER(symbol) = UPPER($2)
    """
    result = await conn.execute(query, portfolio_id, symbol)
    return "DELETE 1" in result or " 1" in result

# ============================================================================
# Transaction Logging and Management
# ============================================================================

async def get_transactions(conn: asyncpg.Connection, portfolio_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Retrieve all transactions for a portfolio using raw SQL with asyncpg."""
    query = """
        SELECT id, portfolio_id, symbol, quantity, price, transaction_type, timestamp
        FROM portfolio_transactions
        WHERE portfolio_id = $1
        ORDER BY timestamp DESC
    """
    rows = await conn.fetch(query, portfolio_id)
    return [dict(row) for row in rows]

async def record_transaction(
    conn: asyncpg.Connection,
    portfolio_id: uuid.UUID,
    symbol: str,
    quantity: float,
    price: float,
    transaction_type: str
) -> Dict[str, Any]:
    """
    Log a buy/sell transaction and automatically update corresponding holding
    using raw SQL inside an asyncpg transaction block.
    """
    transaction_type = transaction_type.upper()
    if transaction_type not in ("BUY", "SELL"):
        raise ValueError("Transaction type must be BUY or SELL")

    transaction_id = uuid.uuid4()
    
    async with conn.transaction():
        # 1. Insert transaction
        tx_query = """
            INSERT INTO portfolio_transactions (id, portfolio_id, symbol, quantity, price, transaction_type)
            VALUES ($1, $2, UPPER($3), $4, $5, $6)
            RETURNING id, portfolio_id, symbol, quantity, price, transaction_type, timestamp
        """
        tx_row = await conn.fetchrow(tx_query, transaction_id, portfolio_id, symbol, quantity, price, transaction_type)
        
        # 2. Fetch current holding for updates
        current_holding = await get_holding(conn, portfolio_id, symbol)
        
        if transaction_type == "BUY":
            if current_holding:
                current_qty = float(current_holding["quantity"])
                current_avg = float(current_holding["average_buy_price"])
                
                new_qty = current_qty + quantity
                new_avg = ((current_qty * current_avg) + (quantity * price)) / new_qty
                
                # Update holding
                update_query = """
                    UPDATE holdings
                    SET quantity = $1, average_buy_price = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE portfolio_id = $3 AND UPPER(symbol) = UPPER($4)
                """
                await conn.execute(update_query, new_qty, new_avg, portfolio_id, symbol)
            else:
                # Create holding
                await upsert_holding(conn, portfolio_id, symbol, quantity, price)
                
        elif transaction_type == "SELL":
            if not current_holding:
                raise ValueError(f"Cannot sell symbol '{symbol}' as you do not hold any shares.")
                
            current_qty = float(current_holding["quantity"])
            if current_qty < quantity:
                raise ValueError(f"Insufficient quantity to sell. You hold {current_qty} shares of '{symbol}' but tried to sell {quantity}.")
                
            new_qty = current_qty - quantity
            
            if new_qty == 0:
                # Delete holding row completely
                await delete_holding(conn, portfolio_id, symbol)
            else:
                # Update holding row with reduced quantity (average cost remains unchanged)
                update_query = """
                    UPDATE holdings
                    SET quantity = $1, updated_at = CURRENT_TIMESTAMP
                    WHERE portfolio_id = $2 AND UPPER(symbol) = UPPER($3)
                """
                await conn.execute(update_query, new_qty, portfolio_id, symbol)
                
        return dict(tx_row) if tx_row else {}


# ============================================================================
# News, Sentiment Analyses, and Suggestions CRUD
# ============================================================================

async def upsert_holding_suggestion(
    conn: asyncpg.Connection,
    portfolio_id: uuid.UUID,
    symbol: str,
    suggested_stop_loss: Optional[float],
    risk_signal: str,
    reasoning: Optional[str],
    quarterly_targets: Optional[dict]
) -> Dict[str, Any]:
    """Upsert an AI-generated holding suggestion, stop loss, risk indicator, and quarterly price targets."""
    import json
    query = """
        INSERT INTO holding_suggestions (portfolio_id, symbol, suggested_stop_loss, risk_signal, reasoning, quarterly_targets, updated_at)
        VALUES ($1, UPPER($2), $3, $4, $5, $6::jsonb, CURRENT_TIMESTAMP)
        ON CONFLICT (portfolio_id, symbol)
        DO UPDATE SET
            suggested_stop_loss = EXCLUDED.suggested_stop_loss,
            risk_signal = EXCLUDED.risk_signal,
            reasoning = EXCLUDED.reasoning,
            quarterly_targets = EXCLUDED.quarterly_targets,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id, portfolio_id, symbol, suggested_stop_loss, risk_signal, reasoning, quarterly_targets, created_at, updated_at
    """
    qt_json = json.dumps(quarterly_targets) if quarterly_targets is not None else None
    row = await conn.fetchrow(query, portfolio_id, symbol, suggested_stop_loss, risk_signal, reasoning, qt_json)
    return dict(row) if row else {}


async def get_holding_suggestions(conn: asyncpg.Connection, portfolio_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Retrieve all suggestions (including stop-loss, risk flags, and quarterly targets) for a portfolio."""
    import json
    query = """
        SELECT id, portfolio_id, symbol, suggested_stop_loss, risk_signal, reasoning, quarterly_targets, created_at, updated_at
        FROM holding_suggestions
        WHERE portfolio_id = $1
    """
    rows = await conn.fetch(query, portfolio_id)
    results = []
    for row in rows:
        d = dict(row)
        if d.get("quarterly_targets") and isinstance(d["quarterly_targets"], str):
            try:
                d["quarterly_targets"] = json.loads(d["quarterly_targets"])
            except Exception:
                pass
        results.append(d)
    return results


async def save_stock_news(
    conn: asyncpg.Connection,
    symbol: str,
    title: str,
    content: Optional[str],
    source: Optional[str],
    url: Optional[str],
    published_at: Optional[datetime]
) -> Dict[str, Any]:
    """Save raw stock news articles, avoiding duplicate URLs for the same symbol."""
    check_query = "SELECT id FROM stock_news WHERE url = $1 AND symbol = UPPER($2) LIMIT 1"
    existing = await conn.fetchrow(check_query, url, symbol)
    if existing:
        return dict(existing)
        
    query = """
        INSERT INTO stock_news (symbol, title, content, source, url, published_at)
        VALUES (UPPER($1), $2, $3, $4, $5, $6)
        RETURNING id, symbol, title, content, source, url, published_at, created_at
    """
    row = await conn.fetchrow(query, symbol, title, content, source, url, published_at)
    return dict(row) if row else {}


async def save_news_analysis(
    conn: asyncpg.Connection,
    news_id: uuid.UUID,
    symbol: str,
    sentiment: str,
    impact_level: str,
    impact_type: str,
    summary: str,
    price_effect: Optional[str]
) -> Dict[str, Any]:
    """Save Gemini AI sentiment & impact analysis for a news article."""
    check_query = "SELECT id FROM news_analyses WHERE news_id = $1 LIMIT 1"
    existing = await conn.fetchrow(check_query, news_id)
    if existing:
        return dict(existing)
        
    query = """
        INSERT INTO news_analyses (news_id, symbol, sentiment, impact_level, impact_type, summary, price_effect)
        VALUES ($1, UPPER($2), $3, $4, $5, $6, $7)
        RETURNING id, news_id, symbol, sentiment, impact_level, impact_type, summary, price_effect, created_at
    """
    row = await conn.fetchrow(query, news_id, symbol, sentiment, impact_level, impact_type, summary, price_effect)
    return dict(row) if row else {}


async def get_news_for_holdings(conn: asyncpg.Connection, portfolio_id: uuid.UUID, limit_per_stock: int = 5) -> List[Dict[str, Any]]:
    """Retrieve the latest news articles and AI analyses for a portfolio's holdings in the last 24 hours."""
    query = """
        WITH ranked_news AS (
            SELECT 
                sn.id as news_id,
                sn.symbol,
                sn.title,
                sn.content,
                sn.source,
                sn.url,
                sn.published_at,
                sn.created_at as news_created_at,
                na.id as analysis_id,
                na.sentiment,
                na.impact_level,
                na.impact_type,
                na.summary as ai_summary,
                na.price_effect,
                ROW_NUMBER() OVER (PARTITION BY sn.symbol ORDER BY sn.published_at DESC) as rn
            FROM stock_news sn
            JOIN holdings h ON UPPER(sn.symbol) = UPPER(h.symbol)
            LEFT JOIN news_analyses na ON sn.id = na.news_id
            WHERE h.portfolio_id = $1 AND sn.published_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )
        SELECT * FROM ranked_news WHERE rn <= $2
    """
    rows = await conn.fetch(query, portfolio_id, limit_per_stock)
    return [dict(row) for row in rows]


async def get_portfolio_news_feed(
    conn: asyncpg.Connection,
    portfolio_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
    sentiment: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve the latest news articles and AI analyses for stocks held in a specific portfolio, sorted chronologically.
    """
    query = """
        SELECT 
            sn.id as news_id,
            sn.symbol,
            sn.title,
            sn.content,
            sn.source,
            sn.url,
            sn.published_at,
            na.id as analysis_id,
            na.sentiment,
            na.impact_level,
            na.impact_type,
            na.summary as ai_summary,
            na.price_effect
        FROM stock_news sn
        JOIN holdings h ON UPPER(sn.symbol) = UPPER(h.symbol)
        LEFT JOIN news_analyses na ON sn.id = na.news_id
        WHERE h.portfolio_id = $1
    """
    params = [portfolio_id]
    
    if sentiment:
        params.append(sentiment.strip().upper())
        query += f" AND UPPER(na.sentiment) = ${len(params)}"
        
    query += f" ORDER BY sn.published_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, offset])
    
    rows = await conn.fetch(query, *params)
    return [dict(row) for row in rows]



