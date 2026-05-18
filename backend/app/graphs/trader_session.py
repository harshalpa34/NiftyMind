import logging
from typing import TypedDict, Annotated
from datetime import datetime
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.models.trader import BehaviorFlagType, FlagSeverity


logger = logging.getLogger(__name__)


class TraderSessionState(TypedDict):
    """State for trader session graph execution"""
    session_id: str
    user_id: str
    trades: Annotated[list, add]
    behavior_flags: Annotated[list, add]
    total_pnl: float
    consecutive_losses: int
    consecutive_wins: int
    total_trades: int
    open_trade_count: int
    guardrail_active: bool
    last_analysis: str
    created_at: str
    updated_at: str


def process_trade(state: TraderSessionState) -> dict:
    """
    Process a trade action (open or close)
    
    Args:
        state: Current trader session state
        
    Returns:
        Updated state fields
    """
    if not state.get("trades"):
        return {}
    
    # Get the last trade record
    last_trade = state["trades"][-1]
    action = last_trade.get("action")
    
    updated_fields = {
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if action == "OPEN":
        # Opening a new trade
        updated_fields["open_trade_count"] = state.get("open_trade_count", 0) + 1
        updated_fields["total_trades"] = state.get("total_trades", 0) + 1
    
    elif action == "CLOSE":
        # Closing a trade
        pnl = last_trade.get("pnl", 0)
        updated_fields["total_pnl"] = state.get("total_pnl", 0) + pnl
        updated_fields["open_trade_count"] = state.get("open_trade_count", 1) - 1
        
        # Update win/loss streaks
        if pnl < 0:
            # Loss
            updated_fields["consecutive_losses"] = state.get("consecutive_losses", 0) + 1
            updated_fields["consecutive_wins"] = 0
        elif pnl > 0:
            # Profit
            updated_fields["consecutive_wins"] = state.get("consecutive_wins", 0) + 1
            updated_fields["consecutive_losses"] = 0
    
    return updated_fields


def detect_behavior(state: TraderSessionState) -> dict:
    """
    Detect behavioral issues and set guardrails
    
    Args:
        state: Current trader session state
        
    Returns:
        Updated flags and guardrail status
    """
    new_flags = []
    guardrail_active = state.get("guardrail_active", False)
    
    # Check for revenge trading (3+ consecutive losses)
    consecutive_losses = state.get("consecutive_losses", 0)
    if consecutive_losses >= 3:
        new_flags.append({
            "flag_type": BehaviorFlagType.REVENGE_TRADE.value,
            "severity": FlagSeverity.HIGH.value,
            "description": f"Detected {consecutive_losses} consecutive losses - potential revenge trading",
            "detected_at": datetime.utcnow().isoformat(),
            "trade_id": None
        })
        guardrail_active = True
        logger.warning(
            "Revenge trading detected",
            extra={
                "session_id": state.get("session_id"),
                "consecutive_losses": consecutive_losses
            }
        )
    
    # Check for overtrading (more than 10 trades)
    total_trades = state.get("total_trades", 0)
    if total_trades > 10:
        new_flags.append({
            "flag_type": BehaviorFlagType.OVERTRADING.value,
            "severity": FlagSeverity.MEDIUM.value,
            "description": f"Excessive trading activity: {total_trades} trades executed",
            "detected_at": datetime.utcnow().isoformat(),
            "trade_id": None
        })
    
    return {
        "behavior_flags": new_flags,
        "guardrail_active": guardrail_active
    }


def build_trader_graph() -> StateGraph:
    """
    Build the LangGraph state machine for trader sessions
    
    Returns:
        Compiled StateGraph with process_trade and detect_behavior nodes
    """
    graph = StateGraph(TraderSessionState)
    
    # Add nodes
    graph.add_node("process_trade", process_trade)
    graph.add_node("detect_behavior", detect_behavior)
    
    # Add edges
    graph.add_edge(START, "process_trade")
    graph.add_edge("process_trade", "detect_behavior")
    graph.add_edge("detect_behavior", END)
    
    return graph


# Memory checkpointer for session persistence
_checkpointer = MemorySaver()

# Compiled trader graph
trader_graph = build_trader_graph().compile(checkpointer=_checkpointer)
