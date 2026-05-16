from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "message": "NiftyMind API is running"}


@router.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API info"""
    return {
        "name": "NiftyMind GenAI API",
        "version": "1.0.0",
        "description": "A modern GenAI backend built with FastAPI",
        "endpoints": {
            "health": "/api/v1/health",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }
