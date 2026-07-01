import logging
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from app.analytics.fno.models.option_chain import OptionChainSnapshot, OptionChainMetrics
from app.analytics.fno.models.oi_delta import OIDeltaReport
from app.analytics.fno.models.analysis import FullAnalysisResponse, MarketNarrative
from app.analytics.fno.services.oi_parser import oi_parser
from app.analytics.fno.services.oi_tracker import oi_tracker
from app.analytics.fno.services.nlp_translator import nlp_translator


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


@router.post(
    "/option-chain/analyse",
    response_model=FullAnalysisResponse,
    status_code=200
)
async def analyse_option_chain(snapshot: OptionChainSnapshot) -> FullAnalysisResponse:
    """
    Complete analysis pipeline: metrics, delta tracking, and AI narrative
    
    Accepts raw option chain data and returns:
    - Current metrics (PCR, max pain, sentiment)
    - Delta report with OI spike detection (if previous snapshot exists)
    - AI-generated market narrative (Claude-powered)
    
    Pipeline:
    1. Process snapshot with oi_tracker (metrics + optional delta)
    2. Generate narrative via Claude NLP translator
    3. Return full analysis response
    
    Falls back to rule-based narrative if Claude API is unavailable.
    """
    logger.info(
        "Option chain analysis pipeline triggered",
        extra={
            "snapshot_id": snapshot.snapshot_id,
            "underlying": snapshot.underlying,
            "strikes_count": len(snapshot.strikes)
        }
    )
    
    # Step 1: Process snapshot with tracking (metrics + delta)
    metrics, delta_report = oi_tracker.process_snapshot(snapshot)
    
    # Step 2: Generate narrative via NLP translator
    narrative = await nlp_translator.translate(metrics, delta_report)
    
    # Step 3: Return full analysis
    return FullAnalysisResponse(
        underlying=snapshot.underlying,
        spot_price=snapshot.spot_price,
        is_baseline=(delta_report is None),
        metrics=metrics,
        delta=delta_report,
        narrative=narrative
    )
