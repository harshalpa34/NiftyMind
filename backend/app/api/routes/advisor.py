import uuid
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg

from app.auth.dependencies import CurrentUser
from app.db.session import get_raw_db
from app.db.crud.portfolio import get_portfolio, get_holdings, get_transactions, get_stock_prices
from app.services.portfolio_risk import portfolio_risk_service
from app.services.behavior_analyzer import behavior_analyzer
from app.services.portfolio_advisor import portfolio_advisor

router = APIRouter(prefix="/portfolio-summary", tags=["AI Portfolio Advisor"])

@router.get("/{portfolio_id}", status_code=status.HTTP_200_OK)
async def api_get_portfolio_summary(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """
    Generate comprehensive AI-powered observations for a portfolio.
    
    Orchestrates holdings, risk analysis, behavioral signal checks, and
    corporate earnings transcripts QA via RAG to synthesize a SEBI-compliant
    report outlining portfolio health and fundamentals.
    """
    # 1. Verify portfolio exists and belongs to the user
    portfolio = await get_portfolio(conn, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )
        
    # 2. Fetch holdings and transactions
    holdings = await get_holdings(conn, portfolio_id)
    transactions = await get_transactions(conn, portfolio_id)
    
    # 2.5 Fetch current stock prices from DB
    symbols = [h["symbol"].upper() for h in holdings]
    price_map = await get_stock_prices(conn, symbols)
    
    # 3. Calculate risk metrics
    risk_metrics = portfolio_risk_service.calculate_risk_metrics(holdings, price_map)
    
    # 4. Analyze behavioral flags
    behavioral_flags = behavior_analyzer.analyze_portfolio(holdings, transactions, price_map)
    
    # 5. Generate AI insights
    summary = await portfolio_advisor.generate_portfolio_summary(
        holdings=holdings,
        risk_metrics=risk_metrics,
        behavioral_flags=behavioral_flags
    )
    
    return {
        "portfolio_name": portfolio["name"],
        "risk_metrics": risk_metrics,
        "behavioral_flags": behavioral_flags,
        "ai_observations": summary["advisor_observations"],
        "corporate_highlights": summary["corporate_highlights"]
    }
