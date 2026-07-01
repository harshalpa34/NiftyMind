from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime


class ExpiryType(str, Enum):
    """Option expiry type enumeration"""
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class ContractData(BaseModel):
    """Option contract data (CALL or PUT)"""
    open_interest: int = Field(..., ge=0, description="Open interest count")
    oi_change: int = Field(..., description="OI change from previous day")
    oi_change_percent: float = Field(..., description="OI change percentage")
    volume: int = Field(..., ge=0, description="Trading volume")
    last_traded_price: float = Field(..., ge=0, description="Last traded price")
    implied_volatility: float = Field(..., ge=0, description="Implied volatility")
    bid_price: Optional[float] = Field(None, description="Bid price")
    ask_price: Optional[float] = Field(None, description="Ask price")


class StrikeData(BaseModel):
    """Data for a specific strike price"""
    strike_price: float = Field(..., gt=0, description="Strike price")
    call: Optional[ContractData] = None
    put: Optional[ContractData] = None


class OptionChainSnapshot(BaseModel):
    """Raw option chain snapshot"""
    snapshot_id: str = Field(..., min_length=1, description="Unique snapshot ID")
    underlying: str = Field(..., min_length=1, description="Underlying symbol")
    spot_price: float = Field(..., gt=0, description="Current spot price")
    expiry_date: str = Field(..., description="Expiry date (YYYY-MM-DD)")
    expiry_type: ExpiryType
    timestamp: datetime = Field(..., description="Snapshot timestamp")
    strikes: List[StrikeData] = Field(..., min_length=1, description="Strike data")
    
    @model_validator(mode="after")
    def validate_strikes_ascending(self):
        """Validate strikes are in ascending order"""
        strike_prices = [s.strike_price for s in self.strikes]
        if strike_prices != sorted(strike_prices):
            raise ValueError("Strikes must be in ascending order of strike_price")
        return self
    
    def model_post_init(self, __context):
        """Uppercase underlying symbol"""
        self.underlying = self.underlying.upper()


class OIConcentration(BaseModel):
    """Open interest concentration at specific strike"""
    strike_price: float
    open_interest: int
    oi_change_percent: float
    side: str = Field(..., description="CALL or PUT")


class OptionChainMetrics(BaseModel):
    """Computed option chain metrics and analysis"""
    snapshot_id: str
    underlying: str
    spot_price: float
    expiry_date: str
    timestamp: datetime
    total_call_oi: int
    total_put_oi: int
    pcr: float = Field(..., description="Put-Call Ratio")
    pcr_signal: str = Field(..., description="BULLISH, BEARISH, or NEUTRAL")
    max_pain_strike: float
    max_pain_distance_percent: float
    top_call_oi_strikes: List[OIConcentration]
    top_put_oi_strikes: List[OIConcentration]
    market_sentiment: str
    computed_at: datetime = Field(default_factory=datetime.utcnow)
