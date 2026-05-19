import logging
from typing import TypedDict, Annotated
from datetime import datetime
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.models.trader import BehaviorFlagType, FlagSeverity
from app.services.behavior_analyzer import behavior_analyzer


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
    # Get trades from state
    trades = state.get("trades", [])
    guardrail_active = state.get("guardrail_active", False)
    
    # Call behavior analyzer
    new_flags = behavior_analyzer.analyze(trades, state)
    
    # Check if any HIGH severity flags — activate guardrail
    high_severity_flags = [f for f in new_flags if f.get("severity") == "HIGH"]
    if high_severity_flags:
        guardrail_active = True
        flag_types = [f.get("flag_type") for f in high_severity_flags]
        logger.warning(
            "High-severity behavior flags detected - guardrail activated",
            extra={
                "session_id": state.get("session_id"),
                "flag_count": len(new_flags),
                "high_severity_flags": flag_types
            }
        )
    
    # Return updated state
    if not new_flags:
        return {"guardrail_active": guardrail_active}
    
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
