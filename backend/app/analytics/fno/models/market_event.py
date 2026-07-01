from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Any, Dict
from enum import Enum


class OptionType(str, Enum):
    """Option type enumeration"""
    CALL = "CALL"
    PUT = "PUT"


class EventType(str, Enum):
    """Types of market events"""
    PRICE_UPDATE = "price_update"
    VOLUME_SPIKE = "volume_spike"
    SENTIMENT_CHANGE = "sentiment_change"
    NEWS_ALERT = "news_alert"
    ALERT = "alert"
    OTHER = "other"
    OPTION_CHAIN_UPDATE = "OPTION_CHAIN_UPDATE"
    PRICE_ALERT = "PRICE_ALERT"
    OI_SPIKE = "OI_SPIKE"


class OptionChainData(BaseModel):
    """Nested model for option chain data"""
    strike_price: float = Field(..., gt=0, description="Strike price must be greater than 0")
    option_type: OptionType
    open_interest: int = Field(..., ge=0, description="Open interest must be >= 0")
    oi_change_percent: float
    last_traded_price: float = Field(..., ge=0, description="Last traded price must be >= 0")
    implied_volatility: Optional[float] = Field(None, ge=0, le=200, description="IV between 0-200")


class MarketEventCreate(BaseModel):
    """Schema for creating a new market event"""
    event_type: EventType
    symbol: str = Field(..., description="Stock/crypto symbol (e.g., AAPL, BTC)")
    title: str = Field(..., description="Event title")
    description: str = Field(..., description="Detailed event description")
    severity: int = Field(default=5, ge=1, le=10, description="Severity level (1-10)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "price_update",
                "symbol": "AAPL",
                "title": "Price spike detected",
                "description": "Apple stock jumped 5% in 30 minutes",
                "severity": 7,
                "metadata": {"price": 175.50, "change_percent": 5.2}
            }
        }


class MarketEvent(MarketEventCreate):
    """Schema for market event response"""
    id: int = Field(..., description="Event ID")
    created_at: datetime = Field(..., description="Event creation timestamp")
    processed: bool = Field(default=False, description="Whether event was processed")

    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    """Schema for webhook payload"""
    timestamp: datetime
    event: MarketEvent
    action: str = Field(default="created", description="Action type (created, updated, deleted)")


class WebhookResponse(BaseModel):
    """Schema for webhook response"""
    success: bool
    message: str
    event_id: Optional[int] = None


class MarketEventPayload(BaseModel):
    """Request model for market event webhook"""
    event_id: str = Field(..., min_length=1, description="Unique event identifier")
    event_type: EventType
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    exchange: str = Field(default="NSE", description="Exchange name")
    timestamp: datetime = Field(..., description="Event timestamp (ISO format)")
    option_data: Optional[OptionChainData] = None
    metadata: Optional[dict] = None

    @field_validator("symbol", mode="before")
    @classmethod
    def symbol_to_uppercase(cls, v: str) -> str:
        """Convert symbol to uppercase"""
        return v.upper() if isinstance(v, str) else v


class WebhookAcknowledgment(BaseModel):
    """Response model for webhook acknowledgment"""
    received: bool = True
    event_id: str
    event_type: str
    symbol: str
    message: str
    processed_at: datetime = Field(default_factory=datetime.utcnow)
