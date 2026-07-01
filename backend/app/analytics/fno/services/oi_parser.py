import logging
from typing import List
from app.analytics.fno.models.option_chain import (
    OptionChainSnapshot,
    OptionChainMetrics,
    OIConcentration
)
from datetime import datetime


logger = logging.getLogger(__name__)


class OIParserService:
    """Service for parsing and analyzing option chain metrics"""
    
    def parse(self, snapshot: OptionChainSnapshot) -> OptionChainMetrics:
        """
        Parse option chain snapshot and compute metrics
        
        Args:
            snapshot: Raw option chain data
            
        Returns:
            Computed metrics and analysis
        """
        logger.info(
            "Parsing option chain",
            extra={
                "snapshot_id": snapshot.snapshot_id,
                "underlying": snapshot.underlying,
                "strikes_count": len(snapshot.strikes)
            }
        )
        
        # Compute basic metrics
        total_call_oi = self._compute_total_oi(snapshot, "CALL")
        total_put_oi = self._compute_total_oi(snapshot, "PUT")
        pcr = self._compute_pcr(total_call_oi, total_put_oi)
        pcr_signal = self._pcr_to_signal(pcr)
        
        # Compute advanced metrics
        max_pain_strike = self._compute_max_pain(snapshot)
        max_pain_distance_percent = (
            ((max_pain_strike - snapshot.spot_price) / snapshot.spot_price) * 100
        )
        
        # Get top OI strikes
        top_call_strikes = self._get_top_oi_strikes(snapshot, "CALL", top_n=3)
        top_put_strikes = self._get_top_oi_strikes(snapshot, "PUT", top_n=3)
        
        # Determine market sentiment based on metrics
        market_sentiment = self._determine_sentiment(pcr_signal, max_pain_distance_percent)
        
        logger.info(
            "Option chain parsed successfully",
            extra={
                "snapshot_id": snapshot.snapshot_id,
                "pcr": pcr,
                "pcr_signal": pcr_signal,
                "max_pain": max_pain_strike,
                "sentiment": market_sentiment
            }
        )
        
        return OptionChainMetrics(
            snapshot_id=snapshot.snapshot_id,
            underlying=snapshot.underlying,
            spot_price=snapshot.spot_price,
            expiry_date=snapshot.expiry_date,
            timestamp=snapshot.timestamp,
            total_call_oi=total_call_oi,
            total_put_oi=total_put_oi,
            pcr=pcr,
            pcr_signal=pcr_signal,
            max_pain_strike=max_pain_strike,
            max_pain_distance_percent=round(max_pain_distance_percent, 2),
            top_call_oi_strikes=top_call_strikes,
            top_put_oi_strikes=top_put_strikes,
            market_sentiment=market_sentiment
        )
    
    def _compute_total_oi(self, snapshot: OptionChainSnapshot, side: str) -> int:
        """
        Compute total open interest for a side (CALL or PUT)
        
        Args:
            snapshot: Option chain snapshot
            side: "CALL" or "PUT"
            
        Returns:
            Total OI for the side
        """
        total_oi = 0
        
        for strike in snapshot.strikes:
            if side == "CALL" and strike.call:
                total_oi += strike.call.open_interest
            elif side == "PUT" and strike.put:
                total_oi += strike.put.open_interest
        
        return total_oi
    
    def _compute_pcr(self, total_call_oi: int, total_put_oi: int) -> float:
        """
        Compute Put-Call Ratio
        
        Args:
            total_call_oi: Total call open interest
            total_put_oi: Total put open interest
            
        Returns:
            PCR ratio (rounded to 4 decimals)
        """
        if total_call_oi == 0:
            logger.warning("Total call OI is zero, returning 0 for PCR")
            return 0.0
        
        pcr = total_put_oi / total_call_oi
        return round(pcr, 4)
    
    def _pcr_to_signal(self, pcr: float) -> str:
        """
        Convert PCR to market signal
        
        Args:
            pcr: Put-Call Ratio
            
        Returns:
            Signal: "BULLISH", "BEARISH", or "NEUTRAL"
        """
        if pcr >= 1.2:
            return "BULLISH"
        elif pcr <= 0.7:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def _compute_max_pain(self, snapshot: OptionChainSnapshot) -> float:
        """
        Compute max pain (maximum pain at expiry)
        
        Algorithm: For each strike as potential expiry price, compute total
        cost for all option buyers at that price, return strike with minimum
        total pain.
        
        Time Complexity: O(n²) where n = number of strikes
        
        Args:
            snapshot: Option chain snapshot
            
        Returns:
            Strike price with maximum pain
        """
        if not snapshot.strikes:
            return snapshot.spot_price
        
        min_pain = float('inf')
        max_pain_strike = snapshot.spot_price
        
        # For each strike as potential expiry price
        for expiry_strike in snapshot.strikes:
            expiry_price = expiry_strike.strike_price
            total_pain = 0
            
            # Calculate pain for all other strikes at this expiry price
            for strike in snapshot.strikes:
                # Call pain: max(0, expiry_price - strike_price) * call_oi
                if strike.call:
                    call_pain = max(0, expiry_price - strike.strike_price) * strike.call.open_interest
                    total_pain += call_pain
                
                # Put pain: max(0, strike_price - expiry_price) * put_oi
                if strike.put:
                    put_pain = max(0, strike.strike_price - expiry_price) * strike.put.open_interest
                    total_pain += put_pain
            
            # Track the strike with minimum pain
            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = expiry_price
        
        return max_pain_strike
    
    def _get_top_oi_strikes(
        self,
        snapshot: OptionChainSnapshot,
        side: str,
        top_n: int = 3
    ) -> List[OIConcentration]:
        """
        Get top N strikes by open interest for a side
        
        Args:
            snapshot: Option chain snapshot
            side: "CALL" or "PUT"
            top_n: Number of top strikes to return
            
        Returns:
            List of top OI strikes
        """
        oi_data = []
        
        for strike in snapshot.strikes:
            if side == "CALL" and strike.call:
                oi_data.append({
                    "strike_price": strike.strike_price,
                    "open_interest": strike.call.open_interest,
                    "oi_change_percent": strike.call.oi_change_percent,
                    "side": "CALL"
                })
            elif side == "PUT" and strike.put:
                oi_data.append({
                    "strike_price": strike.strike_price,
                    "open_interest": strike.put.open_interest,
                    "oi_change_percent": strike.put.oi_change_percent,
                    "side": "PUT"
                })
        
        # Sort by OI descending and take top N
        oi_data.sort(key=lambda x: x["open_interest"], reverse=True)
        top_strikes = oi_data[:top_n]
        
        return [
            OIConcentration(
                strike_price=item["strike_price"],
                open_interest=item["open_interest"],
                oi_change_percent=item["oi_change_percent"],
                side=item["side"]
            )
            for item in top_strikes
        ]
    
    def _determine_sentiment(self, pcr_signal: str, max_pain_distance_percent: float) -> str:
        """
        Determine overall market sentiment based on metrics
        
        Args:
            pcr_signal: PCR signal (BULLISH, BEARISH, NEUTRAL)
            max_pain_distance_percent: Distance to max pain as percentage
            
        Returns:
            Market sentiment
        """
        # If max pain is far away, sentiment is mixed
        if abs(max_pain_distance_percent) > 5:
            if max_pain_distance_percent > 0:
                return "MODERATELY_BULLISH" if pcr_signal == "BULLISH" else "MODERATELY_BEARISH"
            else:
                return "MODERATELY_BEARISH" if pcr_signal == "BEARISH" else "MODERATELY_BULLISH"
        
        # Max pain is close, use PCR signal
        if pcr_signal == "BULLISH":
            return "BULLISH"
        elif pcr_signal == "BEARISH":
            return "BEARISH"
        else:
            return "NEUTRAL"


# Module-level singleton
oi_parser = OIParserService()
