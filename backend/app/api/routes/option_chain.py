import logging
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from app.models.option_chain import OptionChainSnapshot, OptionChainMetrics
from app.models.oi_delta import OIDeltaReport
from app.services.oi_parser import oi_parser
from app.services.oi_tracker import oi_tracker


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["F&O Engine"])


class StreamResponse(BaseModel):
    """Response model for option chain stream processing"""
    metrics: OptionChainMetrics
    delta: Optional[OIDeltaReport] = None
    is_baseline: bool


@router.post(
    "/option-chain/parse",
    response_model=OptionChainMetrics,
    status_code=200
)
async def parse_option_chain(snapshot: OptionChainSnapshot) -> OptionChainMetrics:
    """
    Parse option chain snapshot and compute metrics
    
    Accepts raw option chain data and returns computed metrics including:
    - Put-Call Ratio (PCR) and market signal
    - Maximum pain calculation
    - Top OI concentration strikes
    - Market sentiment analysis
    """
    logger.info(
        "Option chain parse request received",
        extra={
            "snapshot_id": snapshot.snapshot_id,
            "underlying": snapshot.underlying,
            "strikes_count": len(snapshot.strikes),
            "expiry_date": snapshot.expiry_date
        }
    )
    
    # Parse and compute metrics
    metrics = oi_parser.parse(snapshot)
    
    return metrics


@router.post(
    "/option-chain/stream",
    response_model=StreamResponse,
    status_code=200
)
async def stream_option_chain(snapshot: OptionChainSnapshot) -> StreamResponse:
    """
    Stream option chain snapshot with delta tracking and spike detection
    
    Accepts raw option chain data and returns:
    - Current metrics (PCR, max pain, sentiment)
    - Delta report if previous snapshot exists (PCR change, OI spikes)
    - Baseline flag indicating if this is first snapshot for underlying
    
    On first snapshot for an underlying, returns baseline with delta=None.
    On subsequent snapshots, returns delta analysis with spike alerts.
    """
    logger.info(
        "Option chain stream request received",
        extra={
            "snapshot_id": snapshot.snapshot_id,
            "underlying": snapshot.underlying,
            "strikes_count": len(snapshot.strikes),
            "expiry_date": snapshot.expiry_date
        }
    )
    
    # Process snapshot with tracking
    metrics, delta_report = oi_tracker.process_snapshot(snapshot)
    
    return StreamResponse(
        metrics=metrics,
        delta=delta_report,
        is_baseline=(delta_report is None)
    )
