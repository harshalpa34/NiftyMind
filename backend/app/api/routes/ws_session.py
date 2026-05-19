import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websockets.session_connection_manager import session_conn_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/session/{session_id}")
async def websocket_session_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for session-scoped alerts and heartbeats
    
    Args:
        websocket: WebSocket connection
        session_id: Session identifier
    """
    # Accept and register connection
    await session_conn_manager.connect(session_id, websocket)
    
    try:
        while True:
            # Wait for heartbeat
            data = await websocket.receive_text()
            
            logger.debug(
                "Heartbeat received from session",
                extra={
                    "session_id": session_id,
                    "data": data
                }
            )
            
            # Echo back heartbeat
            await session_conn_manager.send_message(
                session_id,
                {
                    "type": "HEARTBEAT",
                    "session_id": session_id
                }
            )
    
    except WebSocketDisconnect:
        session_conn_manager.disconnect(session_id)
    
    except Exception as e:
        logger.error(
            f"WebSocket error in session {session_id}: {e}",
            extra={
                "session_id": session_id,
                "error": str(e)
            }
        )
        session_conn_manager.disconnect(session_id)
