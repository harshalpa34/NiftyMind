import json
import logging
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SessionConnectionManager:
    """Manager for session-scoped WebSocket connections"""
    
    def __init__(self):
        """Initialize connection pool"""
        self._connections: dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """
        Accept and register a WebSocket connection for a session
        
        Args:
            session_id: Session identifier
            websocket: WebSocket connection
        """
        await websocket.accept()
        
        # Close any existing connection for this session
        if session_id in self._connections:
            try:
                await self._connections[session_id].close()
            except Exception:
                pass
        
        # Store connection
        self._connections[session_id] = websocket
        
        logger.info(
            "Session WebSocket connected",
            extra={
                "session_id": session_id,
                "total_sessions": len(self._connections)
            }
        )
        
        # Send connection confirmation
        await self.send_message(
            session_id,
            {
                "type": "CONNECTED",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def disconnect(self, session_id: str) -> None:
        """
        Disconnect and remove a WebSocket connection
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._connections:
            self._connections.pop(session_id)
            logger.info(
                "Session WebSocket disconnected",
                extra={
                    "session_id": session_id,
                    "total_sessions": len(self._connections)
                }
            )
    
    async def send_message(self, session_id: str, payload: dict) -> bool:
        """
        Send a message to a specific session
        
        Args:
            session_id: Session identifier
            payload: Message payload dict
            
        Returns:
            True if sent, False if connection not found or error
        """
        websocket = self._connections.get(session_id)
        if not websocket:
            return False
        
        try:
            await websocket.send_text(json.dumps(payload, default=str))
            return True
        except Exception as e:
            logger.warning(
                f"Failed to send WebSocket message to session {session_id}",
                extra={
                    "session_id": session_id,
                    "error": str(e)
                }
            )
            self.disconnect(session_id)
            return False
    
    async def send_guardrail_alert(
        self,
        session_id: str,
        new_flags: list[dict],
        session_summary: dict
    ) -> bool:
        """
        Send guardrail alert to session WebSocket
        
        Args:
            session_id: Session identifier
            new_flags: List of new behavior flag dicts
            session_summary: Session summary with pnl and loss metrics
            
        Returns:
            True if sent, False otherwise
        """
        if not new_flags:
            return False
        
        # Determine overall severity
        overall_severity = "MEDIUM"
        if any(f.get("severity") == "HIGH" for f in new_flags):
            overall_severity = "HIGH"
        
        # Extract flag types
        flag_types = [f.get("flag_type") for f in new_flags]
        
        # Build alert message
        message = self._build_alert_message(
            flag_types,
            overall_severity,
            session_summary
        )
        
        # Build payload
        payload = {
            "type": "GUARDRAIL_ALERT",
            "session_id": session_id,
            "severity": overall_severity,
            "flags": new_flags,
            "flag_types": flag_types,
            "message": message,
            "total_pnl": session_summary.get("total_pnl", 0.0),
            "consecutive_losses": session_summary.get("consecutive_losses", 0),
            "guardrail_active": session_summary.get("guardrail_active", False),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send message
        sent = await self.send_message(session_id, payload)
        
        if sent:
            logger.warning(
                "Guardrail alert sent to session",
                extra={
                    "session_id": session_id,
                    "flag_types": flag_types,
                    "severity": overall_severity
                }
            )
        
        return sent
    
    def is_connected(self, session_id: str) -> bool:
        """
        Check if a session is connected
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if connected, False otherwise
        """
        return session_id in self._connections
    
    def _build_alert_message(self, flag_types: list[str], severity: str, summary: dict) -> str:
        """
        Build alert message based on flags detected
        
        Args:
            flag_types: List of flag type strings
            severity: Overall severity (HIGH or MEDIUM)
            summary: Session summary dict
            
        Returns:
            Alert message string
        """
        consecutive_losses = summary.get("consecutive_losses", 0)
        total_pnl = summary.get("total_pnl", 0.0)
        
        if "REVENGE_TRADE" in flag_types and consecutive_losses >= 3:
            drawdown = abs(total_pnl)
            return (
                f"⚠️  REVENGE TRADING DETECTED: {consecutive_losses} consecutive losses "
                f"with ${drawdown:,.2f} drawdown. Consider taking a break."
            )
        elif "FOMO" in flag_types:
            return (
                "⚠️  FOMO DETECTED: Rapid re-entry after loss. "
                "Emotional trading behavior identified. Take a cooling-off period."
            )
        elif "POSITION_SIZING" in flag_types:
            return (
                "⚠️  EXCESSIVE POSITION SIZING: Current position exceeds safe limits. "
                "Reduce position size to manage risk."
            )
        elif "OVERTRADING" in flag_types:
            return (
                "⚠️  OVERTRADING DETECTED: Too many trades in short time window. "
                "Slow down and focus on quality over quantity."
            )
        else:
            return (
                f"⚠️  BEHAVIORAL ALERT: Detected {len(flag_types)} trading behavior flag(s). "
                "Review your trading decisions."
            )


# Module-level singleton
session_conn_manager = SessionConnectionManager()
