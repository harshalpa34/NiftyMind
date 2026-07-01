import logging
from datetime import datetime
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.crud.session import (
    create_user_session,
    get_user_sessions,
    verify_session_ownership,
)
from app.db.session import get_db
from app.models.trader import (
    AddTradeRequest,
    CloseTradeRequest,
    TraderSessionSummary
)
from app.services.session_manager import session_manager


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Behavioral Guardrail"])


class UserSessionListItem(BaseModel):
    """User session list item response model."""
    session_id: str
    label: Optional[str] = None
    created_at: datetime
    total_trades: int
    total_pnl: float
    guardrail_active: bool

    class Config:
        from_attributes = True


@router.post("/sessions", status_code=201, response_model=TraderSessionSummary)
async def create_session(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new trader session
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        TraderSessionSummary for new session
    """
    user_id = str(current_user.id)
    logger.info("Creating trader session", extra={"user_id": user_id})
    
    # Create session via LangGraph
    summary = await session_manager.create_session(user_id)
    
    # Track session ownership in database
    await create_user_session(
        db=db,
        user_id=current_user.id,
        session_id=summary.session_id,
        label=None,
    )
    
    logger.info(
        "Session created and tracked",
        extra={"user_id": user_id, "session_id": summary.session_id}
    )
    
    return summary


@router.get("/sessions", response_model=list[UserSessionListItem])
async def list_sessions(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[UserSessionListItem]:
    """
    List all active sessions for current user
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of UserSessionListItem with session metadata
    """
    user_id = str(current_user.id)
    logger.info("Listing user sessions", extra={"user_id": user_id})
    
    # Get sessions from database
    db_sessions = await get_user_sessions(db, current_user.id)
    
    result = []
    for db_session in db_sessions:
        # Get LangGraph state for each session
        state = session_manager.get_session(db_session.session_id)
        
        if state is None:
            logger.warning(
                "Session state not found",
                extra={"user_id": user_id, "session_id": db_session.session_id}
            )
            continue
        
        result.append(
            UserSessionListItem(
                session_id=db_session.session_id,
                label=db_session.label,
                created_at=db_session.created_at,
                total_trades=state.total_trades,
                total_pnl=state.total_pnl,
                guardrail_active=state.guardrail_active,
            )
        )
    
    logger.info(
        "Sessions listed",
        extra={"user_id": user_id, "count": len(result)}
    )
    
    return result


@router.post("/sessions/{session_id}/trades", status_code=201, response_model=TraderSessionSummary)
async def add_trade(
    session_id: str,
    request: AddTradeRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new trade to session
    
    Args:
        session_id: Session identifier
        request: AddTradeRequest with trade details
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated TraderSessionSummary
        
    Raises:
        HTTPException 403 if user does not own the session
        HTTPException 404 if session not found
    """
    user_id = str(current_user.id)
    
    # Verify ownership before allowing trade
    is_owner = await verify_session_ownership(db, current_user.id, session_id)
    if not is_owner:
        logger.warning(
            "Unauthorized trade attempt",
            extra={"user_id": user_id, "session_id": session_id}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session not found or access denied."
        )
    
    logger.info(
        "Adding trade to session",
        extra={
            "user_id": user_id,
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
async def close_trade(
    session_id: str,
    request: CloseTradeRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Close an open trade in session
    
    Args:
        session_id: Session identifier
        request: CloseTradeRequest with trade_id and exit_price
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated TraderSessionSummary
        
    Raises:
        HTTPException 403 if user does not own the session
        HTTPException 404 if session or trade not found
    """
    user_id = str(current_user.id)
    
    # Verify ownership before allowing trade close
    is_owner = await verify_session_ownership(db, current_user.id, session_id)
    if not is_owner:
        logger.warning(
            "Unauthorized trade close attempt",
            extra={"user_id": user_id, "session_id": session_id}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session not found or access denied."
        )
    
    logger.info(
        "Closing trade in session",
        extra={
            "user_id": user_id,
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


@router.get("/sessions/{session_id}/recover", response_model=TraderSessionSummary, status_code=200)
async def recover_session(
    session_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Recover a persisted session after server restart
    
    Args:
        session_id: Session identifier
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        TraderSessionSummary
        
    Raises:
        HTTPException 403 if user does not own the session
        HTTPException 404 if session not found or expired
    """
    user_id = str(current_user.id)
    
    # Verify ownership before allowing recovery
    is_owner = await verify_session_ownership(db, current_user.id, session_id)
    if not is_owner:
        logger.warning(
            "Unauthorized session recovery attempt",
            extra={"user_id": user_id, "session_id": session_id}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session not found or access denied."
        )
    
    logger.info(
        "Recovering trader session",
        extra={"user_id": user_id, "session_id": session_id}
    )
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found or expired"
        )
    
    return session
