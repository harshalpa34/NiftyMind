from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from app.analytics.fno.models.option_chain import OptionChainMetrics
from app.analytics.fno.models.oi_delta import OIDeltaReport


class MarketNarrative(BaseModel):
    """AI-generated narrative analysis of market structure and dynamics"""
    snapshot_summary: str
    delta_insight: Optional[str] = None
    key_levels: Optional[str] = None
    sentiment_summary: str
    generated_by: str = "gemini-2.5-flash"
    is_fallback: bool = False
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class FullAnalysisResponse(BaseModel):
    """Complete analysis response with metrics, deltas, and AI narrative"""
    underlying: str
    spot_price: float
    is_baseline: bool
    metrics: OptionChainMetrics
    delta: Optional[OIDeltaReport] = None
    narrative: MarketNarrative
    analysed_at: datetime = Field(default_factory=datetime.utcnow)
