import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.core.logging import setup_logging
from app.core.exceptions import register_exception_handlers
from app.middleware.request_id import RequestIDMiddleware
from app.api.routes.health import router as health_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.option_chain import router as option_chain_router
from app.api.routes.ws_feed import router as ws_feed_router
from app.api.routes.ws_session import router as ws_session_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.rag import router as rag_router
from app.websockets.feed_simulator import run_feed_simulator
import app.graphs.trader_session as trader_session_module

# Get settings
settings = get_settings()

# Global variable to hold simulator task
simulator_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global simulator_task
    
    # Startup
    setup_logging()  # Initialize structured logging FIRST
    logger = logging.getLogger(__name__)
    logger.info("🚀 NiftyMind API starting...")
    
    # Initialize trader session graph with SqliteSaver
    trader_session_module.trader_graph = trader_session_module.initialize_graph()
    logger.info("Trader session graph ready")
    
    # Start feed simulator
    simulator_task = asyncio.create_task(run_feed_simulator())
    
    yield
    
    # Shutdown
    logger.info("🛑 NiftyMind API shutting down...")
    
    # Cancel simulator task
    simulator_task.cancel()
    try:
        await simulator_task
    except asyncio.CancelledError:
        pass


# Initialize FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="A modern GenAI backend built with FastAPI and async/await",
    debug=settings.debug,
    lifespan=lifespan
)

# Add middleware (order matters - request ID should be first)
app.add_middleware(RequestIDMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(option_chain_router)
app.include_router(ws_feed_router)
app.include_router(ws_session_router)
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
