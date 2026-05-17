import logging
import sys
from pythonjsonlogger import jsonlogger
from app.config import get_settings


def setup_logging() -> None:
    """Setup structured JSON logging for the application"""
    settings = get_settings()
    
    # Create JSON formatter
    json_formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
        rename_fields={'asctime': 'timestamp', 'levelname': 'level'}
    )
    
    # Create stream handler for stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(json_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Clear existing handlers
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    
    # Silence uvicorn loggers
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.WARNING)
    
    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info(
        "Structured logging initialized",
        extra={
            "service": "NiftyMind",
            "debug": settings.debug
        }
    )
