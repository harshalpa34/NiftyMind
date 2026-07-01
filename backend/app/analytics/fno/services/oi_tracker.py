import logging
from typing import Optional, Tuple, Dict
from datetime import datetime

from app.analytics.fno.models.option_chain import OptionChainSnapshot, OptionChainMetrics
from app.analytics.fno.models.oi_delta import (
    OIDeltaReport,
    OISpikeAlert,
    SpikeSeverity,
    SpikeType,
    PCRSentiment
)
from app.analytics.fno.services.oi_parser import oi_parser


logger = logging.getLogger(__name__)


class OITrackerService:
    """Service for tracking OI changes and detecting spikes"""
    
    # Spike detection thresholds (% change)
    SPIKE_THRESHOLD_HIGH = 50.0
    SPIKE_THRESHOLD_MEDIUM = 30.0
    SPIKE_THRESHOLD_LOW = 15.0
    
    # PCR sentiment classification thresholds
    PCR_STRONG_THRESHOLD = 0.25
    PCR_MODERATE_THRESHOLD = 0.15
    
    def __init__(self):
        """Initialize tracker with empty state"""
        self._state: Dict[str, Tuple[OptionChainSnapshot, OptionChainMetrics]] = {}
    
    def process_snapshot(
        self,
        snapshot: OptionChainSnapshot
    ) -> Tuple[OptionChainMetrics, Optional[OIDeltaReport]]:
        """
        Process option chain snapshot and detect changes
        
        Args:
            snapshot: Current option chain snapshot
            
        Returns:
            Tuple of (metrics, delta_report or None if baseline)
        """
        # Parse snapshot to get metrics
        metrics = oi_parser.parse(snapshot)
        
        # Check if we have previous state
        underlying = snapshot.underlying
        
        if underlying in self._state:
            prev_snapshot, prev_metrics = self._state[underlying]
            
            # Compute delta
            delta_report = self._compute_delta(
                prev_snapshot, prev_metrics,
                snapshot, metrics
            )
            
            logger.info(
                "OI delta computed",
                extra={
                    "underlying": underlying,
                    "pcr_delta": delta_report.pcr_delta,
                    "sentiment": delta_report.pcr_sentiment,
                    "spike_count": delta_report.spike_count,
                    "critical": delta_report.has_critical_spike
                }
            )
            
            # Update state
            self._state[underlying] = (snapshot, metrics)
            
            return metrics, delta_report
        else:
            # Establish baseline
            logger.info(
                "OI baseline established",
                extra={
                    "underlying": underlying,
                    "snapshot_id": snapshot.snapshot_id,
                    "pcr": metrics.pcr
                }
            )
            
            # Store state
            self._state[underlying] = (snapshot, metrics)
            
            return metrics, None
    
    def _compute_delta(
        self,
        prev_snapshot: OptionChainSnapshot,
        prev_metrics: OptionChainMetrics,
        curr_snapshot: OptionChainSnapshot,
        curr_metrics: OptionChainMetrics
    ) -> OIDeltaReport:
        """
        Compute delta between two snapshots
        
        Args:
            prev_snapshot: Previous option chain snapshot
            prev_metrics: Previous computed metrics
            curr_snapshot: Current option chain snapshot
            curr_metrics: Current computed metrics
            
        Returns:
            Delta report with all analysis
        """
        # Compute PCR delta
        pcr_delta = round(curr_metrics.pcr - prev_metrics.pcr, 4)
        
        # Classify PCR sentiment
        pcr_sentiment = self._classify_pcr_sentiment(pcr_delta)
        
        # Detect OI spikes
        spike_alerts = self._detect_oi_spikes(prev_snapshot, curr_snapshot)
        
        # Compute time delta
        time_delta_seconds = (
            curr_snapshot.timestamp - prev_snapshot.timestamp
        ).total_seconds()
        
        # Check for critical spikes
        has_critical_spike = any(
            alert.severity == SpikeSeverity.HIGH
            for alert in spike_alerts
        )
        
        # Build summary
        summary = self._build_summary(
            curr_snapshot.underlying,
            pcr_sentiment,
            spike_alerts,
            curr_metrics
        )
        
        return OIDeltaReport(
            underlying=curr_snapshot.underlying,
            current_snapshot_id=curr_snapshot.snapshot_id,
            previous_snapshot_id=prev_snapshot.snapshot_id,
            current_timestamp=curr_snapshot.timestamp,
            previous_timestamp=prev_snapshot.timestamp,
            time_delta_seconds=time_delta_seconds,
            pcr_previous=round(prev_metrics.pcr, 4),
            pcr_current=round(curr_metrics.pcr, 4),
            pcr_delta=pcr_delta,
            pcr_sentiment=pcr_sentiment,
            total_call_oi_previous=prev_metrics.total_call_oi,
            total_call_oi_current=curr_metrics.total_call_oi,
            total_put_oi_previous=prev_metrics.total_put_oi,
            total_put_oi_current=curr_metrics.total_put_oi,
            spike_alerts=spike_alerts,
            spike_count=len(spike_alerts),
            has_critical_spike=has_critical_spike,
            summary=summary
        )
    
    def _detect_oi_spikes(
        self,
        prev_snapshot: OptionChainSnapshot,
        curr_snapshot: OptionChainSnapshot
    ) -> list[OISpikeAlert]:
        """
        Detect significant OI changes between snapshots
        
        Args:
            prev_snapshot: Previous option chain snapshot
            curr_snapshot: Current option chain snapshot
            
        Returns:
            List of spike alerts sorted by magnitude
        """
        alerts = []
        
        # Build lookup dict from previous snapshot
        prev_strikes = {
            strike.strike_price: strike
            for strike in prev_snapshot.strikes
        }
        
        # Check each current strike against previous
        for curr_strike in curr_snapshot.strikes:
            prev_strike = prev_strikes.get(curr_strike.strike_price)
            
            if not prev_strike:
                # New strike, skip
                continue
            
            # Check CALL side
            if curr_strike.call and prev_strike.call:
                alert = self._evaluate_spike(
                    curr_strike.strike_price,
                    "CALL",
                    prev_strike.call.open_interest,
                    curr_strike.call.open_interest
                )
                if alert:
                    alerts.append(alert)
            
            # Check PUT side
            if curr_strike.put and prev_strike.put:
                alert = self._evaluate_spike(
                    curr_strike.strike_price,
                    "PUT",
                    prev_strike.put.open_interest,
                    curr_strike.put.open_interest
                )
                if alert:
                    alerts.append(alert)
        
        # Sort by absolute change % descending
        alerts.sort(
            key=lambda a: abs(a.oi_change_percent),
            reverse=True
        )
        
        return alerts
    
    def _evaluate_spike(
        self,
        strike_price: float,
        side: str,
        oi_before: int,
        oi_after: int
    ) -> Optional[OISpikeAlert]:
        """
        Evaluate if OI change constitutes a spike
        
        Args:
            strike_price: Strike price level
            side: "CALL" or "PUT"
            oi_before: OI before
            oi_after: OI after
            
        Returns:
            OISpikeAlert if spike detected, None otherwise
        """
        # Return None if no previous OI (can't calculate percentage change)
        if oi_before == 0:
            return None
        
        # Compute percentage change
        change_pct = ((oi_after - oi_before) / oi_before) * 100
        
        # Return None if below threshold
        if abs(change_pct) < self.SPIKE_THRESHOLD_LOW:
            return None
        
        # Classify severity
        abs_change = abs(change_pct)
        if abs_change >= self.SPIKE_THRESHOLD_HIGH:
            severity = SpikeSeverity.HIGH
        elif abs_change >= self.SPIKE_THRESHOLD_MEDIUM:
            severity = SpikeSeverity.MEDIUM
        else:
            severity = SpikeSeverity.LOW
        
        # Determine spike type
        spike_type = SpikeType.BUILDUP if oi_after > oi_before else SpikeType.UNWINDING
        
        # Get interpretation
        interpretation = self._interpret_spike(
            side,
            spike_type,
            strike_price,
            change_pct
        )
        
        return OISpikeAlert(
            strike_price=strike_price,
            side=side,
            oi_before=oi_before,
            oi_after=oi_after,
            oi_change_percent=round(change_pct, 2),
            spike_type=spike_type,
            severity=severity,
            interpretation=interpretation
        )
    
    def _classify_pcr_sentiment(self, pcr_delta: float) -> PCRSentiment:
        """
        Classify PCR sentiment based on delta
        
        Args:
            pcr_delta: Change in PCR
            
        Returns:
            PCRSentiment classification
        """
        if pcr_delta >= self.PCR_STRONG_THRESHOLD:
            return PCRSentiment.STRONG_BULLISH_SHIFT
        elif pcr_delta >= self.PCR_MODERATE_THRESHOLD:
            return PCRSentiment.BULLISH_SHIFT
        elif pcr_delta <= -self.PCR_STRONG_THRESHOLD:
            return PCRSentiment.STRONG_BEARISH_SHIFT
        elif pcr_delta <= -self.PCR_MODERATE_THRESHOLD:
            return PCRSentiment.BEARISH_SHIFT
        else:
            return PCRSentiment.STABLE
    
    def _interpret_spike(
        self,
        side: str,
        spike_type: SpikeType,
        strike_price: float,
        change_pct: float
    ) -> str:
        """
        Generate human-readable interpretation of spike
        
        Args:
            side: "CALL" or "PUT"
            spike_type: BUILDUP or UNWINDING
            strike_price: Strike level
            change_pct: Percentage change
            
        Returns:
            Interpretation string
        """
        side_name = side.lower()
        direction = "increasing" if spike_type == SpikeType.BUILDUP else "decreasing"
        
        if spike_type == SpikeType.BUILDUP:
            if side == "CALL":
                return (
                    f"Bullish buildup: {abs(change_pct):.1f}% increase in "
                    f"{side_name} OI at {strike_price}, traders building "
                    f"bullish positions/support"
                )
            else:
                return (
                    f"Bearish buildup: {abs(change_pct):.1f}% increase in "
                    f"{side_name} OI at {strike_price}, traders building "
                    f"bearish positions/resistance"
                )
        else:  # UNWINDING
            if side == "CALL":
                return (
                    f"Call unwinding: {abs(change_pct):.1f}% decrease in "
                    f"{side_name} OI at {strike_price}, bullish positions "
                    f"being squared off"
                )
            else:
                return (
                    f"Put unwinding: {abs(change_pct):.1f}% decrease in "
                    f"{side_name} OI at {strike_price}, bearish positions "
                    f"being squared off"
                )
    
    def _build_summary(
        self,
        underlying: str,
        pcr_sentiment: PCRSentiment,
        spike_alerts: list[OISpikeAlert],
        curr_metrics: OptionChainMetrics
    ) -> str:
        """
        Build summary string for delta report
        
        Args:
            underlying: Underlying symbol
            pcr_sentiment: PCR sentiment classification
            spike_alerts: List of detected spikes
            curr_metrics: Current metrics
            
        Returns:
            Summary string
        """
        sentiment_display = pcr_sentiment.value.replace("_", " ")
        base_summary = (
            f"{underlying} | PCR: {curr_metrics.pcr:.4f} | "
            f"{sentiment_display} | Spikes: {len(spike_alerts)}"
        )
        
        # Append critical spike information
        critical_spikes = [
            a for a in spike_alerts
            if a.severity == SpikeSeverity.HIGH
        ]
        
        if critical_spikes:
            strike_list = ", ".join(
                f"{s.strike_price} ({s.side})"
                for s in critical_spikes
            )
            base_summary += f" | ⚠️ CRITICAL at {strike_list}"
        
        return base_summary


# Module-level singleton
oi_tracker = OITrackerService()
