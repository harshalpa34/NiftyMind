from fastapi import APIRouter, HTTPException, status, Header
from typing import List, Optional, Annotated
import logging
from app.models.market_event import (
    MarketEvent, 
    MarketEventCreate, 
    WebhookPayload,
    WebhookResponse,
    MarketEventPayload,
    WebhookAcknowledgment
)
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["market-events"])

# In-memory storage (replace with database later)
events_db: dict[int, MarketEvent] = {}
event_counter = 0


@router.post("/events", response_model=MarketEvent, status_code=status.HTTP_201_CREATED)
async def create_event(event_create: MarketEventCreate) -> MarketEvent:
    """Create a new market event"""
    global event_counter
    event_counter += 1
    
    event = MarketEvent(
        id=event_counter,
        created_at=datetime.utcnow(),
        **event_create.model_dump()
    )
    
    events_db[event.id] = event
    return event


@router.get("/events", response_model=List[MarketEvent])
async def list_events(
    symbol: Optional[str] = None,
    skip: int = 0,
    limit: int = 10
) -> List[MarketEvent]:
    """List all market events with optional filtering"""
    events = list(events_db.values())
    
    if symbol:
        events = [e for e in events if e.symbol.upper() == symbol.upper()]
    
    return events[skip : skip + limit]


@router.get("/events/{event_id}", response_model=MarketEvent)
async def get_event(event_id: int) -> MarketEvent:
    """Get a specific market event by ID"""
    if event_id not in events_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found"
        )
    return events_db[event_id]


@router.put("/events/{event_id}", response_model=MarketEvent)
async def update_event(event_id: int, event_update: MarketEventCreate) -> MarketEvent:
    """Update an existing market event"""
    if event_id not in events_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found"
        )
    
    updated_event = MarketEvent(
        id=event_id,
        created_at=events_db[event_id].created_at,
        **event_update.model_dump()
    )
    
    events_db[event_id] = updated_event
    return updated_event


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: int) -> None:
    """Delete a market event"""
    if event_id not in events_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found"
        )
    del events_db[event_id]


@router.post("/webhooks/events", response_model=WebhookResponse)
async def receive_webhook(payload: WebhookPayload) -> WebhookResponse:
    """
    Receive webhook events from external services
    This endpoint accepts market events from monitoring systems
    """
    try:
        # Store the event
        global event_counter
        event_counter += 1
        
        event = MarketEvent(
            id=event_counter,
            created_at=datetime.utcnow(),
            **payload.event.model_dump(exclude={"id", "created_at"})
        )
        
        events_db[event.id] = event
        
        return WebhookResponse(
            success=True,
            message=f"Event received and stored successfully",
            event_id=event.id
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.get("/events/summary/stats")
async def get_event_stats() -> dict:
    """Get summary statistics about events"""
    return {
        "total_events": len(events_db),
        "events_by_type": {},
        "symbols": list(set(e.symbol for e in events_db.values())),
        "average_severity": (
            sum(e.severity for e in events_db.values()) / len(events_db) 
            if events_db else 0
        )
    }


@router.post(
    "/webhook/market-event",
    response_model=WebhookAcknowledgment,
    status_code=202,
    tags=["Webhooks"]
)
async def receive_market_event(
    payload: MarketEventPayload,
    x_webhook_secret: Annotated[str | None, Header()] = None,
) -> WebhookAcknowledgment:
    """
    Receive and acknowledge market event webhooks
    
    Validates webhook secret header if provided.
    Expected header: X-Webhook-Secret
    """
    # Validate webhook secret if provided
    if x_webhook_secret is not None:
        if x_webhook_secret != "tradepulse-dev-secret":
            logger.warning(f"Invalid webhook secret attempt for event {payload.event_id}")
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook secret"
            )
    
    # Log the received event
    logger.info(
        f"Webhook received - event_id: {payload.event_id}, "
        f"event_type: {payload.event_type.value}, symbol: {payload.symbol}"
    )
    
    # Return acknowledgment
    return WebhookAcknowledgment(
        received=True,
        event_id=payload.event_id,
        event_type=payload.event_type.value,
        symbol=payload.symbol,
        message=f"Event {payload.event_id} received and queued for processing"
    )
