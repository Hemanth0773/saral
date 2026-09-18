"""
Health check endpoint.
Used to verify the API is running and healthy.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema"""
    status: str
    service: str
    version: str
    timestamp: str
    environment: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the status of the API and basic service information.

    Returns:
        HealthResponse with status ok
    """
    logger.debug("Health check requested")

    return HealthResponse(
        status="ok",
        service=settings.APP_NAME,
        version=settings.VERSION,
        timestamp=datetime.utcnow().isoformat(),
        environment=settings.ENVIRONMENT
    )
