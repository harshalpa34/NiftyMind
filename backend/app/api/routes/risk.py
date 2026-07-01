import uuid
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg

from app.auth.dependencies import CurrentUser
from app.db.session import get_raw_db
from app.db.crud.portfolio import get_portfolio, get_holdings
from app.services.portfolio_risk import portfolio_risk_service

router = APIRouter(prefix="/risk-analysis", tags=["Portfolio Risk Engine"])

@router.get("/{portfolio_id}", status_code=status.HTTP_200_OK)
async def api_get_risk_analysis(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """
    Calculate and retrieve risk analysis for a portfolio.
    
    Includes sector exposure, concentration weights, and HHI diversification score.
    """
    # 1. Verify portfolio exists and belongs to the user
    portfolio = await get_portfolio(conn, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )
        
    # 2. Fetch holdings
    holdings = await get_holdings(conn, portfolio_id)
    
    # 3. Calculate metrics
    metrics = portfolio_risk_service.calculate_risk_metrics(holdings)
    return metrics
