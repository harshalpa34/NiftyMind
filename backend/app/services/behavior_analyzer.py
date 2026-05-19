import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BehaviorAnalyzerService:
    """Service for detecting behavioral patterns in trading activity"""
    
    # Configuration constants
    FOMO_TIME_WINDOW_SECONDS = 300  # 5 minutes
    REVENGE_POSITION_MULTIPLIER = 1.5  # 50% larger position
    OVERTRADING_WINDOW_MINUTES = 30
    OVERTRADING_MAX_TRADES = 5  # Max trades in window
    POSITION_SIZING_MULTIPLIER = 2.0  # 2x average
    CONSECUTIVE_LOSS_THRESHOLD = 3
    
    def analyze(self, trades: list[dict], state: dict) -> list[dict]:
        """
        Analyze all behavioral patterns in trading activity
        
        Args:
            trades: List of all trade records (open and close)
            state: Current session state with pnl and loss counters
            
        Returns:
            List of new behavior flag dicts detected
        """
        # Filter trades by action
        open_trades = [t for t in trades if t.get("action") == "OPEN"]
        close_trades = [t for t in trades if t.get("action") == "CLOSE"]
        
        # Get latest open trade for use in detectors
        latest_open = open_trades[-1] if open_trades else None
        
        # Collect all detected flags
        new_flags = []
        
        # Run all detectors
        if flag := self._detect_consecutive_losses(state, latest_open):
            new_flags.append(flag)
            logger.warning(
                "Behavior flag detected: REVENGE_TRADE",
                extra={
                    "flag_type": flag.get("flag_type"),
                    "severity": flag.get("severity"),
                    "session_id": state.get("session_id"),
                    "trade_id": flag.get("trade_id")
                }
            )
        
        if flag := self._detect_fomo(open_trades, close_trades, latest_open):
            new_flags.append(flag)
            logger.warning(
                "Behavior flag detected: FOMO",
                extra={
                    "flag_type": flag.get("flag_type"),
                    "severity": flag.get("severity"),
                    "session_id": state.get("session_id"),
                    "trade_id": flag.get("trade_id")
                }
            )
        
        if flag := self._detect_revenge_position_sizing(open_trades, close_trades, latest_open):
            new_flags.append(flag)
            logger.warning(
                "Behavior flag detected: POSITION_SIZING (Revenge)",
                extra={
                    "flag_type": flag.get("flag_type"),
                    "severity": flag.get("severity"),
                    "session_id": state.get("session_id"),
                    "trade_id": flag.get("trade_id")
                }
            )
        
        if flag := self._detect_overtrading(open_trades, close_trades):
            new_flags.append(flag)
            logger.warning(
                "Behavior flag detected: OVERTRADING",
                extra={
                    "flag_type": flag.get("flag_type"),
                    "severity": flag.get("severity"),
                    "session_id": state.get("session_id"),
                    "trade_id": flag.get("trade_id")
                }
            )
        
        if flag := self._detect_excessive_position_sizing(open_trades, close_trades, latest_open):
            new_flags.append(flag)
            logger.warning(
                "Behavior flag detected: POSITION_SIZING (Excessive)",
                extra={
                    "flag_type": flag.get("flag_type"),
                    "severity": flag.get("severity"),
                    "session_id": state.get("session_id"),
                    "trade_id": flag.get("trade_id")
                }
            )
        
        return new_flags
    
    def _detect_consecutive_losses(self, state: dict, latest_open: Optional[dict]) -> Optional[dict]:
        """
        Detect revenge trading pattern from consecutive losses
        
        Args:
            state: Current session state
            latest_open: Latest open trade record
            
        Returns:
            Flag dict or None
        """
        consecutive_losses = state.get("consecutive_losses", 0)
        
        if consecutive_losses < self.CONSECUTIVE_LOSS_THRESHOLD:
            return None
        
        if not latest_open:
            return None
        
        return {
            "flag_type": "REVENGE_TRADE",
            "severity": "HIGH",
            "description": f"{consecutive_losses} consecutive losses detected. Consider a cooling-off period before next trade.",
            "detected_at": datetime.utcnow().isoformat(),
            "trade_id": latest_open.get("trade_id")
        }
    
    def _detect_fomo(
        self,
        open_trades: list[dict],
        close_trades: list[dict],
        latest_open: Optional[dict]
    ) -> Optional[dict]:
        """
        Detect FOMO (fear of missing out) — quick re-entry after loss
        
        Args:
            open_trades: List of open trade records
            close_trades: List of close trade records
            latest_open: Latest open trade record
            
        Returns:
            Flag dict or None
        """
        try:
            # Need at least 2 open trades to detect FOMO pattern
            if len(open_trades) < 2 or not close_trades:
                return None
            
            if not latest_open:
                return None
            
            # Find latest losing close trade
            latest_losing_close = None
            for close_trade in reversed(close_trades):
                if close_trade.get("pnl", 0) < 0:
                    latest_losing_close = close_trade
                    break
            
            if not latest_losing_close:
                return None
            
            # Parse timestamps
            try:
                close_time = datetime.fromisoformat(latest_losing_close.get("timestamp", ""))
                open_time = datetime.fromisoformat(latest_open.get("timestamp", ""))
            except (ValueError, TypeError):
                return None
            
            # Calculate delta
            delta_seconds = (open_time - close_time).total_seconds()
            
            # FOMO if re-entered within time window (but not same second)
            if 0 < delta_seconds < self.FOMO_TIME_WINDOW_SECONDS:
                return {
                    "flag_type": "FOMO",
                    "severity": "MEDIUM",
                    "description": f"Quick re-entry detected: new position opened {int(delta_seconds)} seconds after previous loss. Emotional trading detected.",
                    "detected_at": datetime.utcnow().isoformat(),
                    "trade_id": latest_open.get("trade_id")
                }
            
            return None
        
        except Exception as e:
            logger.debug(f"FOMO detection error: {e}")
            return None
    
    def _detect_revenge_position_sizing(
        self,
        open_trades: list[dict],
        close_trades: list[dict],
        latest_open: Optional[dict]
    ) -> Optional[dict]:
        """
        Detect revenge trading with increased position size
        
        Args:
            open_trades: List of open trade records
            close_trades: List of close trade records
            latest_open: Latest open trade record
            
        Returns:
            Flag dict or None
        """
        try:
            if not latest_open or len(close_trades) < 1:
                return None
            
            # Find latest losing close trade
            latest_losing_close = None
            for close_trade in reversed(close_trades):
                if close_trade.get("pnl", 0) < 0:
                    latest_losing_close = close_trade
                    break
            
            if not latest_losing_close:
                return None
            
            # Get quantities
            current_qty = latest_open.get("quantity", 0)
            
            # Find original open trade for the losing position
            original_trade_id = None
            for trade in reversed(open_trades[:-1]):  # Exclude latest open
                if trade.get("trade_id") == latest_losing_close.get("trade_id"):
                    original_trade_id = trade
                    break
            
            if not original_trade_id:
                return None
            
            original_qty = original_trade_id.get("quantity", 0)
            
            # Check if revenge sizing occurred
            if original_qty > 0 and current_qty > original_qty * self.REVENGE_POSITION_MULTIPLIER:
                return {
                    "flag_type": "POSITION_SIZING",
                    "severity": "HIGH",
                    "description": f"Revenge sizing detected: position increased from {original_qty} to {current_qty} ({self.REVENGE_POSITION_MULTIPLIER}x multiplier) after loss.",
                    "detected_at": datetime.utcnow().isoformat(),
                    "trade_id": latest_open.get("trade_id")
                }
            
            return None
        
        except Exception as e:
            logger.debug(f"Revenge position sizing detection error: {e}")
            return None
    
    def _detect_overtrading(
        self,
        open_trades: list[dict],
        close_trades: list[dict]
    ) -> Optional[dict]:
        """
        Detect overtrading — too many trades in short time window
        
        Args:
            open_trades: List of open trade records
            close_trades: List of close trade records
            
        Returns:
            Flag dict or None
        """
        try:
            all_trades = open_trades + close_trades
            
            if len(all_trades) < self.OVERTRADING_MAX_TRADES:
                return None
            
            # Get latest trade timestamp
            latest_trade = all_trades[-1] if all_trades else None
            if not latest_trade:
                return None
            
            try:
                latest_time = datetime.fromisoformat(latest_trade.get("timestamp", ""))
            except (ValueError, TypeError):
                return None
            
            # Count trades in time window
            window_start = latest_time.timestamp() - (self.OVERTRADING_WINDOW_MINUTES * 60)
            trades_in_window = 0
            
            for trade in all_trades:
                try:
                    trade_time = datetime.fromisoformat(trade.get("timestamp", ""))
                    if trade_time.timestamp() >= window_start:
                        trades_in_window += 1
                except (ValueError, TypeError):
                    continue
            
            if trades_in_window > self.OVERTRADING_MAX_TRADES:
                latest_open = next((t for t in reversed(open_trades)), None)
                return {
                    "flag_type": "OVERTRADING",
                    "severity": "MEDIUM",
                    "description": f"Overtrading detected: {trades_in_window} trades in {self.OVERTRADING_WINDOW_MINUTES} minutes. Risk of emotional decision-making.",
                    "detected_at": datetime.utcnow().isoformat(),
                    "trade_id": latest_open.get("trade_id") if latest_open else None
                }
            
            return None
        
        except Exception as e:
            logger.debug(f"Overtrading detection error: {e}")
            return None
    
    def _detect_excessive_position_sizing(
        self,
        open_trades: list[dict],
        close_trades: list[dict],
        latest_open: Optional[dict]
    ) -> Optional[dict]:
        """
        Detect excessive position sizing relative to historical average
        
        Args:
            open_trades: List of open trade records
            close_trades: List of close trade records
            latest_open: Latest open trade record
            
        Returns:
            Flag dict or None
        """
        try:
            if not latest_open or len(open_trades) < 2:
                return None
            
            # Calculate average position size from previous trades
            previous_quantities = [t.get("quantity", 0) for t in open_trades[:-1]]
            if not previous_quantities:
                return None
            
            avg_quantity = sum(previous_quantities) / len(previous_quantities)
            current_qty = latest_open.get("quantity", 0)
            
            # Check if excessive
            if avg_quantity > 0 and current_qty > avg_quantity * self.POSITION_SIZING_MULTIPLIER:
                return {
                    "flag_type": "POSITION_SIZING",
                    "severity": "MEDIUM",
                    "description": f"Excessive position size: {current_qty} units vs average {avg_quantity:.1f} units ({self.POSITION_SIZING_MULTIPLIER}x multiplier).",
                    "detected_at": datetime.utcnow().isoformat(),
                    "trade_id": latest_open.get("trade_id")
                }
            
            return None
        
        except Exception as e:
            logger.debug(f"Excessive position sizing detection error: {e}")
            return None


# Module-level singleton
behavior_analyzer = BehaviorAnalyzerService()
