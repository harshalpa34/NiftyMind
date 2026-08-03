import uuid
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg
from typing import List

from app.auth.dependencies import CurrentUser
from app.db.session import get_raw_db
from app.db.crud.portfolio import get_portfolio, get_holdings, get_transactions, get_stock_prices
from app.services.behavior_analyzer import behavior_analyzer

router = APIRouter(prefix="/behavioral-analysis", tags=["Behavioral Guardrails"])

@router.get("/{portfolio_id}", response_model=List[dict], status_code=status.HTTP_200_OK)
async def api_get_behavioral_analysis(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """
    Perform behavioral guardrails analysis on a user's portfolio.
    
    Checks transaction patterns and holdings for overtrading, revenge trading,
    FOMO, and excessive asset concentration.
    """
    # 1. Verify portfolio exists and belongs to the user
    portfolio = await get_portfolio(conn, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )
        
    # 2. Fetch holdings and transaction logs
    holdings = await get_holdings(conn, portfolio_id)
    transactions = await get_transactions(conn, portfolio_id)
    
    # 2.5 Fetch current stock prices from DB
    symbols = [h["symbol"].upper() for h in holdings]
    price_map = await get_stock_prices(conn, symbols)
    
    # 3. Analyze patterns
    flags = behavior_analyzer.analyze_portfolio(holdings, transactions, price_map)
    return flags
