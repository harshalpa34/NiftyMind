import logging
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict

from app.analytics.fno.models.option_chain import (
    OptionChainSnapshot,
    StrikeData,
    ContractData,
    ExpiryType
)
from app.analytics.fno.services.oi_tracker import oi_tracker
from app.analytics.fno.services.nlp_translator import nlp_translator
from app.analytics.fno.websockets.connection_manager import connection_manager


logger = logging.getLogger(__name__)

# Simulator configuration
BASE_SPOT = 24500.0
BASE_STRIKES = [24200, 24300, 24400, 24500, 24600, 24700, 24800]
EXPIRY_DATE = "2025-05-29"
TICK_INTERVAL = 10
UNDERLYING = "NIFTY"

# Base OI values (realistic distribution with ATM having highest OI)
BASE_OI = {
    24200: {"call": 45000, "put": 120000},
    24300: {"call": 85000, "put": 110000},
    24400: {"call": 165000, "put": 95000},
    24500: {"call": 280000, "put": 150000},  # ATM - highest OI
    24600: {"call": 175000, "put": 105000},
    24700: {"call": 92000, "put": 75000},
    24800: {"call": 52000, "put": 45000},
}

# Mutable copy of BASE_OI (updated each tick)
_current_oi: Dict[float, Dict[str, int]] = {
    strike: {"call": oi["call"], "put": oi["put"]}
    for strike, oi in BASE_OI.items()
}

# Snapshot counter (global)
_snapshot_counter: int = 0


def _generate_snapshot() -> OptionChainSnapshot:
    """
    Generate synthetic option chain snapshot
    
    Returns:
        OptionChainSnapshot with synthetic data
    """
    global _snapshot_counter, _current_oi
    
    _snapshot_counter += 1
    
    # Drift spot price ±0.3%
    price_drift = random.uniform(-0.003, 0.003)
    spot_price = BASE_SPOT * (1 + price_drift)
    spot_price = round(spot_price, 2)
    
    # Generate strikes
    strikes = []
    
    for strike_price in BASE_STRIKES:
        # Determine if spike occurs (5% chance)
        has_spike = random.random() < 0.05
        
        if has_spike:
            # 5% spike: 30-80% change
            call_change_pct = random.uniform(0.30, 0.80)
            put_change_pct = random.uniform(0.30, 0.80)
        else:
            # Normal: ±2% change
            call_change_pct = random.uniform(-0.02, 0.02)
            put_change_pct = random.uniform(-0.02, 0.02)
        
        # Compute new OI values
        old_call_oi = _current_oi[strike_price]["call"]
        old_put_oi = _current_oi[strike_price]["put"]
        
        new_call_oi = max(1000, int(old_call_oi * (1 + call_change_pct)))
        new_put_oi = max(1000, int(old_put_oi * (1 + put_change_pct)))
        
        # Update current OI
        _current_oi[strike_price]["call"] = new_call_oi
        _current_oi[strike_price]["put"] = new_put_oi
        
        # Create contract data
        call_data = ContractData(
            open_interest=new_call_oi,
            oi_change=new_call_oi - old_call_oi,
            oi_change_percent=round(call_change_pct * 100, 2),
            volume=random.randint(500, 5000),
            last_traded_price=round(random.uniform(50, 500), 2),
            implied_volatility=round(random.uniform(18, 28), 2),
            bid_price=round(random.uniform(40, 450), 2),
            ask_price=round(random.uniform(50, 500), 2)
        )
        
        put_data = ContractData(
            open_interest=new_put_oi,
            oi_change=new_put_oi - old_put_oi,
            oi_change_percent=round(put_change_pct * 100, 2),
            volume=random.randint(500, 5000),
            last_traded_price=round(random.uniform(10, 300), 2),
            implied_volatility=round(random.uniform(17, 27), 2),
            bid_price=round(random.uniform(10, 280), 2),
            ask_price=round(random.uniform(15, 300), 2)
        )
        
        # Create strike data
        strike_data = StrikeData(
            strike_price=strike_price,
            call=call_data,
            put=put_data
        )
        
        strikes.append(strike_data)
    
    # Create and return snapshot
    expiry_date = datetime.strptime(EXPIRY_DATE, "%Y-%m-%d").date()
    
    snapshot = OptionChainSnapshot(
        snapshot_id=f"syn_{UNDERLYING}_{_snapshot_counter:06d}",
        underlying=UNDERLYING,
        spot_price=spot_price,
        expiry_date=expiry_date,
        expiry_type=ExpiryType.WEEKLY,
        timestamp=datetime.utcnow(),
        strikes=strikes
    )
    
    return snapshot


async def run_feed_simulator() -> None:
    """
    Run synthetic data feed simulator
    
    Continuously generates option chain snapshots and broadcasts to
    connected WebSocket clients. Gracefully handles disconnections
    and API errors.
    """
    print("SIMULATOR FUNCTION ENTERED", flush=True)
    
    logger.info(
        "Feed simulator started",
        extra={
            "underlying": UNDERLYING,
            "tick_interval": TICK_INTERVAL,
            "strikes": len(BASE_STRIKES)
        }
    )
    
    # Wait for initial baseline
    print("SIMULATOR sleeping for 3 seconds...", flush=True)
    await asyncio.sleep(3)
    print("SIMULATOR FIRST SLEEP DONE - ENTERING LOOP", flush=True)
    
    # Check singleton instance
    print(f"SIMULATOR connection_manager id: {id(connection_manager)}", flush=True)
    
    try:
        while True:
            print(f"SIMULATOR TICK - connections: {connection_manager.connection_count}", flush=True)
            
            # Skip if no connections
            if connection_manager.connection_count == 0:
                await asyncio.sleep(TICK_INTERVAL)
                continue
            
            try:
                # Generate snapshot
                snapshot = _generate_snapshot()
                
                logger.info(
                    "Tick generated",
                    extra={
                        "snapshot_id": snapshot.snapshot_id,
                        "spot_price": snapshot.spot_price,
                        "connected_clients": connection_manager.connection_count
                    }
                )
                
                # Process with tracker and translator
                metrics, delta_report = oi_tracker.process_snapshot(snapshot)
                narrative = await nlp_translator.translate(metrics, delta_report)
                
                # Build payload
                payload = {
                    "type": "MARKET_UPDATE",
                    "snapshot_id": snapshot.snapshot_id,
                    "timestamp": snapshot.timestamp.isoformat(),
                    "underlying": snapshot.underlying,
                    "spot_price": snapshot.spot_price,
                    "is_baseline": delta_report is None,
                    "metrics": {
                        "pcr": metrics.pcr,
                        "pcr_signal": metrics.pcr_signal,
                        "max_pain_strike": metrics.max_pain_strike,
                        "total_call_oi": metrics.total_call_oi,
                        "total_put_oi": metrics.total_put_oi,
                        "market_sentiment": metrics.market_sentiment
                    },
                    "delta": None if not delta_report else {
                        "pcr_delta": delta_report.pcr_delta,
                        "pcr_sentiment": delta_report.pcr_sentiment.value,
                        "spike_count": delta_report.spike_count,
                        "has_critical_spike": delta_report.has_critical_spike,
                        "summary": delta_report.summary
                    },
                    "narrative": {
                        "snapshot_summary": narrative.snapshot_summary,
                        "delta_insight": narrative.delta_insight,
                        "key_levels": narrative.key_levels,
                        "sentiment_summary": narrative.sentiment_summary,
                        "is_fallback": narrative.is_fallback
                    }
                }
                
                # Broadcast to clients
                import json
                print(f"SIMULATOR BROADCASTING to {connection_manager.connection_count} clients", flush=True)
                await connection_manager.broadcast(json.dumps(payload))
                print("SIMULATOR BROADCAST COMPLETE", flush=True)
                
                # Wait for next tick
                await asyncio.sleep(TICK_INTERVAL)
                
            except asyncio.CancelledError:
                print("SIMULATOR CANCELLED", flush=True)
                logger.info("Feed simulator cancelled")
                break
            except Exception as e:
                print(f"SIMULATOR ERROR: {e}", flush=True)
                logger.error(
                    "Error in feed simulator tick",
                    exc_info=True,
                    extra={"error": str(e)}
                )
                await asyncio.sleep(TICK_INTERVAL)
                continue
    
    except asyncio.CancelledError:
        logger.info("Feed simulator shutdown")
