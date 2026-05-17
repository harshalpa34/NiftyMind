import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for the application"""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors (422 Unprocessable Entity)"""
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log validation error
        logger.warning(
            "Validation error",
            extra={
                "request_id": request_id,
                "errors": exc.errors()
            }
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "message": "Request validation failed",
                "request_id": request_id,
                "details": exc.errors()
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log HTTP exception
        logger.warning(
            "HTTP exception",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "detail": exc.detail
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Error",
                "message": exc.detail,
                "request_id": request_id
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions (500 Internal Server Error)"""
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log full stack trace
        logger.error(
            "Unhandled exception",
            extra={"request_id": request_id},
            exc_info=True
        )
        
        # Return safe error response without stack trace
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "request_id": request_id
            }
        )
