from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List


class TradeDirection(str, Enum):
    """Direction of a trade"""
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(str, Enum):
    """Status of a trade"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class BehaviorFlagType(str, Enum):
    """Type of behavioral flag detected"""
    FOMO = "FOMO"
    REVENGE_TRADE = "REVENGE_TRADE"
    OVERTRADING = "OVERTRADING"
    POSITION_SIZING = "POSITION_SIZING"


class FlagSeverity(str, Enum):
    """Severity level of behavior flag"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SimulatedTrade(BaseModel):
    """Record of a simulated trade"""
    trade_id: str
    symbol: str
    direction: TradeDirection
    entry_price: float = Field(gt=0)
    quantity: int = Field(gt=0)
    exit_price: Optional[float] = None
    status: TradeStatus
    pnl: Optional[float] = None
    timestamp: datetime
    notes: Optional[str] = None


class BehaviorFlag(BaseModel):
    """Behavioral flag detected during trading"""
    flag_type: BehaviorFlagType
    severity: FlagSeverity
    description: str
    detected_at: datetime
    trade_id: Optional[str] = None


class TraderSessionSummary(BaseModel):
    """Summary of a trader session"""
    session_id: str
    user_id: str
    total_trades: int
    open_trades: int
    open_trade_ids: list[str] = []
    total_pnl: float
    consecutive_losses: int
    consecutive_wins: int
    behavior_flags: List[BehaviorFlag]
    guardrail_active: bool
    last_analysis: str
    created_at: datetime
    updated_at: datetime


class AddTradeRequest(BaseModel):
    """Request to add a new trade"""
    symbol: str
    direction: TradeDirection
    entry_price: float = Field(gt=0)
    quantity: int = Field(gt=0)
    notes: Optional[str] = None


class CloseTradeRequest(BaseModel):
    """Request to close an open trade"""
    trade_id: str
    exit_price: float = Field(gt=0)
