import logging
from fastapi import WebSocket
from typing import List


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time market feed"""
    
    def __init__(self):
        """Initialize with empty connections list"""
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """
        Accept and register a new WebSocket connection
        
        Args:
            websocket: WebSocket connection to accept
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"MANAGER CONNECT called - total now: {len(self.active_connections)}", flush=True)
        logger.info(
            "WebSocket connected",
            extra={"total_connections": self.connection_count}
        )
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection
        
        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"MANAGER DISCONNECT called - total now: {len(self.active_connections)}", flush=True)
        logger.info(
            "WebSocket disconnected",
            extra={"total_connections": self.connection_count}
        )
    
    async def broadcast(self, message: str):
        """
        Broadcast message to all active connections
        
        Args:
            message: JSON string to broadcast
        """
        print(f"MANAGER BROADCAST called - {len(self.active_connections)} connections", flush=True)
        if not self.active_connections:
            return
        
        dead_connections = []
        
        # Send to all active connections
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.append(connection)
        
        # Remove dead connections
        for connection in dead_connections:
            self.disconnect(connection)
        
        logger.debug(
            "Broadcast sent",
            extra={"recipients": len(self.active_connections)}
        )
    
    @property
    def connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)


# Module-level singleton
connection_manager = ConnectionManager()
