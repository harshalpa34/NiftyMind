import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websockets.connection_manager import connection_manager


logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    """
    WebSocket endpoint for real-time market feed
    
    Receives client connections and broadcasts synthetic market data
    updates. Clients can send heartbeat messages to stay connected.
    """
    print(f"WS ROUTE - client connected, calling manager.connect()", flush=True)
    await connection_manager.connect(websocket)
    print(f"WS ROUTE - manager.connect() done", flush=True)
    print(f"WS ROUTE connection_manager id: {id(connection_manager)}", flush=True)
    
    try:
        while True:
            # Wait for client message (heartbeat or keep-alive)
            data = await websocket.receive_text()
            
            # Log first 100 chars of message
            msg_preview = data[:100] if len(data) > 100 else data
            logger.info(
                "WebSocket message received",
                extra={"message": msg_preview}
            )
            
            # Send ACK back to client
            ack = json.dumps({
                "type": "ACK",
                "message": "Message received"
            })
            await websocket.send_text(ack)
    
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(
            "WebSocket error",
            exc_info=True,
            extra={"error": str(e)}
        )
        connection_manager.disconnect(websocket)
