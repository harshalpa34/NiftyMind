import logging
import uuid
from datetime import datetime
from typing import Optional

from app.models.trader import (
    TraderSessionSummary,
    BehaviorFlag,
    BehaviorFlagType,
    FlagSeverity,
    SimulatedTrade,
    TradeDirection,
    TradeStatus
)
from app.graphs.trader_session import trader_graph
from app.websockets.session_connection_manager import session_conn_manager


logger = logging.getLogger(__name__)


class SessionManagerService:
    """Service for managing trader sessions with LangGraph state machine"""
    
    async def create_session(self, user_id: str) -> TraderSessionSummary:
        """
        Create a new trader session
        
        Args:
            user_id: User identifier
            
        Returns:
            TraderSessionSummary for new session
        """
        session_id = str(uuid.uuid4())[:8]
        
        # Initial state
        initial_state = {
            "session_id": session_id,
            "user_id": user_id,
            "trades": [],
            "behavior_flags": [],
            "total_pnl": 0.0,
            "consecutive_losses": 0,
            "consecutive_wins": 0,
            "total_trades": 0,
            "open_trade_count": 0,
            "guardrail_active": False,
            "last_analysis": "Session created",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Invoke graph
        config = {"configurable": {"thread_id": session_id}}
        trader_graph.invoke(initial_state, config=config)
        
        logger.info(
            "Trader session created",
            extra={"session_id": session_id, "user_id": user_id}
        )
        
        return self._get_summary(session_id)
    
    async def add_trade(
        self,
        session_id: str,
        symbol: str,
        direction: TradeDirection,
        entry_price: float,
        quantity: int,
        notes: Optional[str] = None
    ) -> TraderSessionSummary:
        """
        Add an open trade to session
        
        Args:
            session_id: Session identifier
            symbol: Trading symbol
            direction: LONG or SHORT
            entry_price: Entry price
            quantity: Quantity
            notes: Optional trade notes
            
        Returns:
            Updated TraderSessionSummary
        """
        # Capture flag count before trade
        prev_raw_state = self._get_raw_state(session_id)
        prev_flag_count = len(prev_raw_state.get("behavior_flags", [])) if prev_raw_state else 0
        
        trade_id = str(uuid.uuid4())[:8]
        
        # Build trade record
        trade_record = {
            "action": "OPEN",
            "trade_id": trade_id,
            "symbol": symbol,
            "direction": direction.value,
            "entry_price": entry_price,
            "quantity": quantity,
            "status": TradeStatus.OPEN.value,
            "timestamp": datetime.utcnow().isoformat(),
            "notes": notes
        }
        
        # Invoke graph
        config = {"configurable": {"thread_id": session_id}}
        trader_graph.invoke({"trades": [trade_record]}, config=config)
        
        logger.info(
            "Trade opened",
            extra={
                "session_id": session_id,
                "trade_id": trade_id,
                "symbol": symbol,
                "direction": direction.value,
                "entry_price": entry_price
            }
        )
        
        # Get updated summary
        summary = self._get_summary(session_id)
        
        # Detect new flags
        new_flags = summary.behavior_flags[prev_flag_count:] if len(summary.behavior_flags) > prev_flag_count else []
        
        # Send guardrail alert if new flags and session is connected
        if new_flags and session_conn_manager.is_connected(session_id):
            alert_dict = {
                "total_pnl": summary.total_pnl,
                "consecutive_losses": summary.consecutive_losses,
                "guardrail_active": summary.guardrail_active
            }
            # Convert BehaviorFlag objects to dicts for alert
            new_flags_dicts = [
                {
                    "flag_type": f.flag_type.value,
                    "severity": f.severity.value,
                    "description": f.description,
                    "detected_at": f.detected_at.isoformat(),
                    "trade_id": f.trade_id
                }
                for f in new_flags
            ]
            await session_conn_manager.send_guardrail_alert(
                session_id,
                new_flags_dicts,
                alert_dict
            )
        
        return summary
    
    async def close_trade(
        self,
        session_id: str,
        trade_id: str,
        exit_price: float
    ) -> TraderSessionSummary:
        """
        Close an open trade
        
        Args:
            session_id: Session identifier
            trade_id: Trade identifier
            exit_price: Exit price
            
        Returns:
            Updated TraderSessionSummary
        """
        # Capture flag count before trade
        prev_raw_state = self._get_raw_state(session_id)
        if not prev_raw_state:
            raise ValueError(f"Session {session_id} not found")
        prev_flag_count = len(prev_raw_state.get("behavior_flags", []))
        
        # Find the trade
        trades = prev_raw_state.get("trades", [])
        target_trade = None
        for trade in trades:
            if trade.get("trade_id") == trade_id and trade.get("action") == "OPEN":
                target_trade = trade
                break
        
        if not target_trade:
            raise ValueError(f"Open trade {trade_id} not found in session {session_id}")
        
        # Compute PnL
        entry_price = target_trade.get("entry_price", 0)
        quantity = target_trade.get("quantity", 1)
        direction = target_trade.get("direction", "LONG")
        
        if direction == TradeDirection.LONG.value:
            pnl = (exit_price - entry_price) * quantity
        else:  # SHORT
            pnl = (entry_price - exit_price) * quantity
        
        # Build close record
        close_record = {
            "action": "CLOSE",
            "trade_id": trade_id,
            "exit_price": exit_price,
            "pnl": pnl,
            "status": TradeStatus.CLOSED.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Invoke graph
        config = {"configurable": {"thread_id": session_id}}
        trader_graph.invoke({"trades": [close_record]}, config=config)
        
        logger.info(
            "Trade closed",
            extra={
                "session_id": session_id,
                "trade_id": trade_id,
                "exit_price": exit_price,
                "pnl": pnl
            }
        )
        
        # Get updated summary
        summary = self._get_summary(session_id)
        
        # Detect new flags
        new_flags = summary.behavior_flags[prev_flag_count:] if len(summary.behavior_flags) > prev_flag_count else []
        
        # Send guardrail alert if new flags and session is connected
        if new_flags and session_conn_manager.is_connected(session_id):
            alert_dict = {
                "total_pnl": summary.total_pnl,
                "consecutive_losses": summary.consecutive_losses,
                "guardrail_active": summary.guardrail_active
            }
            # Convert BehaviorFlag objects to dicts for alert
            new_flags_dicts = [
                {
                    "flag_type": f.flag_type.value,
                    "severity": f.severity.value,
                    "description": f.description,
                    "detected_at": f.detected_at.isoformat(),
                    "trade_id": f.trade_id
                }
                for f in new_flags
            ]
            await session_conn_manager.send_guardrail_alert(
                session_id,
                new_flags_dicts,
                alert_dict
            )
        
        return summary
    
    def get_session(self, session_id: str) -> Optional[TraderSessionSummary]:
        """
        Get session summary
        
        Args:
            session_id: Session identifier
            
        Returns:
            TraderSessionSummary or None if not found
        """
        raw_state = self._get_raw_state(session_id)
        if not raw_state:
            return None
        
        return self._get_summary(session_id)
    
    def _get_raw_state(self, session_id: str) -> Optional[dict]:
        """
        Get raw state from graph checkpointer
        
        Args:
            session_id: Session identifier
            
        Returns:
            Raw state dict or None if not found
        """
        config = {"configurable": {"thread_id": session_id}}
        state = trader_graph.get_state(config)
        
        if state and state.values:
            return state.values
        return None
    
    def _get_summary(self, session_id: str) -> TraderSessionSummary:
        """
        Build TraderSessionSummary from raw state
        
        Args:
            session_id: Session identifier
            
        Returns:
            TraderSessionSummary
        """
        raw_state = self._get_raw_state(session_id)
        if not raw_state:
            raise ValueError(f"Session {session_id} not found")
        
        # Convert behavior flag dicts to BehaviorFlag objects
        behavior_flags = []
        for flag_dict in raw_state.get("behavior_flags", []):
            behavior_flags.append(BehaviorFlag(
                flag_type=BehaviorFlagType(flag_dict.get("flag_type")),
                severity=FlagSeverity(flag_dict.get("severity")),
                description=flag_dict.get("description", ""),
                detected_at=datetime.fromisoformat(flag_dict.get("detected_at", datetime.utcnow().isoformat())),
                trade_id=flag_dict.get("trade_id")
            ))
        
        # Count open trades and extract open_trade_ids
        open_trades = 0
        open_trade_ids = []
        for trade in raw_state.get("trades", []):
            if trade.get("action") == "OPEN":
                open_trades += 1
                open_trade_ids.append(trade.get("trade_id", ""))
        
        # Create and return summary
        return TraderSessionSummary(
            session_id=raw_state.get("session_id", session_id),
            user_id=raw_state.get("user_id", ""),
            total_trades=raw_state.get("total_trades", 0),
            open_trades=open_trades,
            open_trade_ids=open_trade_ids,
            total_pnl=raw_state.get("total_pnl", 0.0),
            consecutive_losses=raw_state.get("consecutive_losses", 0),
            consecutive_wins=raw_state.get("consecutive_wins", 0),
            behavior_flags=behavior_flags,
            guardrail_active=raw_state.get("guardrail_active", False),
            last_analysis=raw_state.get("last_analysis", ""),
            created_at=datetime.fromisoformat(raw_state.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(raw_state.get("updated_at", datetime.utcnow().isoformat()))
        )


# Module-level singleton
session_manager = SessionManagerService()
