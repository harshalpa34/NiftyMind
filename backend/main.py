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
# from app.api.routes.webhooks import router as webhooks_router
# from app.analytics.fno.routes.option_chain import router as option_chain_router
# from app.analytics.fno.routes.ws_feed import router as ws_feed_router
from app.api.routes.ws_session import router as ws_session_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.rag import router as rag_router
# from app.analytics.fno.websockets.feed_simulator import run_feed_simulator
import app.graphs.trader_session as trader_session_module
from app.graph.neo4j_client import neo4j_client
from app.api.routes.graph import router as graph_router
from app.api.routes.auth import router as auth_router
from app.api.routes.portfolios import router as portfolios_router
from app.api.routes.risk import router as risk_router
from app.api.routes.insights import router as insights_router
from app.api.routes.behavior import router as behavior_router
from app.api.routes.advisor import router as advisor_router
from app.api.routes.news import router as news_router
from app.db.base import get_engine
from app.db.session import get_session_factory, init_pg_pool, close_pg_pool

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
    
    # Initialize async database engine and session factory
    try:
        get_engine()
        get_session_factory()
        await init_pg_pool()
        logger.info("✓ Database engine, session factory, and raw connection pool initialized")
    except ValueError as e:
        logger.warning(f"Database not configured: {e}")
    
    # Initialize trader session graph with SqliteSaver
    trader_session_module.trader_graph = trader_session_module.initialize_graph()
    logger.info("Trader session graph ready")
    
    # Start feed simulator (paused)
    # simulator_task = asyncio.create_task(run_feed_simulator())
    # Connect Neo4j client (may raise if URI not configured)
    try:
        neo4j_client.connect(settings.neo4j_uri, settings.neo4j_username, settings.neo4j_password)
    except Exception as exc:
        logger.warning("Neo4j not connected at startup: %s", exc)
    

    yield
    
    # Shutdown
    logger.info("🛑 NiftyMind API shutting down...")
    
    # Dispose of async database engine and close pg_pool
    try:
        engine = get_engine()
        await engine.dispose()
        await close_pg_pool()
        logger.info("✓ Database engine disposed and raw connection pool closed")
    except Exception as e:
        logger.exception(f"Error disposing database engine: {e}")
    
    # Cancel simulator task (paused)
    if simulator_task:
        simulator_task.cancel()
        try:
            await simulator_task
        except asyncio.CancelledError:
            pass
    # Close neo4j client
    try:
        neo4j_client.close()
    except Exception:
        logger.exception("Error closing Neo4j client")
        



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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origins=["*"],
)

# Register global exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(health_router)
# app.include_router(webhooks_router)
# app.include_router(option_chain_router)
# app.include_router(ws_feed_router)
app.include_router(ws_session_router)
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(portfolios_router, prefix="/api/v1")
app.include_router(risk_router, prefix="/api/v1")
app.include_router(insights_router, prefix="/api/v1")
app.include_router(behavior_router, prefix="/api/v1")
app.include_router(advisor_router, prefix="/api/v1")
app.include_router(news_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
