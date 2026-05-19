import logging
from fastapi import APIRouter, HTTPException, Query

from app.models.trader import (
    AddTradeRequest,
    CloseTradeRequest,
    TraderSessionSummary
)
from app.services.session_manager import session_manager


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Behavioral Guardrail"])


@router.post("/sessions", status_code=201, response_model=TraderSessionSummary)
async def create_session(user_id: str = Query(...)):
    """
    Create a new trader session
    
    Args:
        user_id: User identifier
        
    Returns:
        TraderSessionSummary for new session
    """
    logger.info("Creating trader session", extra={"user_id": user_id})
    return await session_manager.create_session(user_id)


@router.get("/sessions/{session_id}", response_model=TraderSessionSummary)
async def get_session(session_id: str):
    """
    Get trader session summary
    
    Args:
        session_id: Session identifier
        
    Returns:
        TraderSessionSummary
        
    Raises:
        HTTPException 404 if session not found
    """
    logger.info("Retrieving trader session", extra={"session_id": session_id})
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return session


@router.post("/sessions/{session_id}/trades", status_code=201, response_model=TraderSessionSummary)
async def add_trade(session_id: str, request: AddTradeRequest):
    """
    Add a new trade to session
    
    Args:
        session_id: Session identifier
        request: AddTradeRequest with trade details
        
    Returns:
        Updated TraderSessionSummary
        
    Raises:
        HTTPException 404 if session not found
    """
    logger.info(
        "Adding trade to session",
        extra={
            "session_id": session_id,
            "symbol": request.symbol,
            "direction": request.direction.value,
            "entry_price": request.entry_price
        }
    )
    
    try:
        return await session_manager.add_trade(
            session_id=session_id,
            symbol=request.symbol,
            direction=request.direction,
            entry_price=request.entry_price,
            quantity=request.quantity,
            notes=request.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions/{session_id}/trades/close", response_model=TraderSessionSummary)
async def close_trade(session_id: str, request: CloseTradeRequest):
    """
    Close an open trade in session
    
    Args:
        session_id: Session identifier
        request: CloseTradeRequest with trade_id and exit_price
        
    Returns:
        Updated TraderSessionSummary
        
    Raises:
        HTTPException 404 if session or trade not found
    """
    logger.info(
        "Closing trade in session",
        extra={
            "session_id": session_id,
            "trade_id": request.trade_id,
            "exit_price": request.exit_price
        }
    )
    
    try:
        return await session_manager.close_trade(
            session_id=session_id,
            trade_id=request.trade_id,
            exit_price=request.exit_price
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
