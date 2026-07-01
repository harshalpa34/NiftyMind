from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List


class SpikeSeverity(str, Enum):
    """OI spike severity levels"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SpikeType(str, Enum):
    """Type of OI change"""
    BUILDUP = "BUILDUP"
    UNWINDING = "UNWINDING"


class PCRSentiment(str, Enum):
    """PCR sentiment classification"""
    STRONG_BULLISH_SHIFT = "STRONG_BULLISH_SHIFT"
    BULLISH_SHIFT = "BULLISH_SHIFT"
    STABLE = "STABLE"
    BEARISH_SHIFT = "BEARISH_SHIFT"
    STRONG_BEARISH_SHIFT = "STRONG_BEARISH_SHIFT"


class OISpikeAlert(BaseModel):
    """Alert for significant OI changes at a specific strike"""
    strike_price: float
    side: str  # "CALL" or "PUT"
    oi_before: int
    oi_after: int
    oi_change_percent: float
    spike_type: SpikeType
    severity: SpikeSeverity
    interpretation: str


class OIDeltaReport(BaseModel):
    """Report comparing two option chain snapshots with delta analysis"""
    underlying: str
    current_snapshot_id: str
    previous_snapshot_id: str
    current_timestamp: datetime
    previous_timestamp: datetime
    time_delta_seconds: float
    
    # PCR metrics
    pcr_previous: float
    pcr_current: float
    pcr_delta: float
    pcr_sentiment: PCRSentiment
    
    # OI metrics
    total_call_oi_previous: int
    total_call_oi_current: int
    total_put_oi_previous: int
    total_put_oi_current: int
    
    # Spike analysis
    spike_alerts: List[OISpikeAlert] = Field(default_factory=list)
    spike_count: int = 0
    has_critical_spike: bool = False
    
    # Summary and metadata
    summary: str
    computed_at: datetime = Field(default_factory=datetime.utcnow)
