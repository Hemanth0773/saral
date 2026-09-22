"""
Cognitive Accessibility Simplifier for Government Documents
Main FastAPI application entry point
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import health, documents, simplification, extraction, validation, readability, translation, tts, history
from app.schemas.document import ErrorResponse
from app.db import database as db_module


# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize database if enabled
    if settings.USE_DATABASE:
        try:
            db_module.init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            # Do not raise - allow app to start without DB
            # History endpoints will return appropriate errors

    yield

    # Shutdown
    logger.info("Shutting down application")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered system to simplify complex government documents",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom handler for HTTP exceptions to ensure consistent error format"""
    # Extract the actual detail content
    detail = exc.detail

    # If detail is already a dict with the right structure, use it directly
    if isinstance(detail, dict) and "success" in detail:
        content = detail
    elif isinstance(detail, dict) and "detail" in detail and isinstance(detail["detail"], dict) and "success" in detail["detail"]:
        # Handle double-wrapped details
        content = detail["detail"]
    else:
        # Map some status codes to friendly error codes
        error_code = "HTTP_ERROR"
        if exc.status_code == 400:
            error_code = "BAD_REQUEST"
        elif exc.status_code == 401:
            error_code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            error_code = "FORBIDDEN"
        elif exc.status_code == 404:
            error_code = "NOT_FOUND"
        elif exc.status_code == 413:
            error_code = "FILE_TOO_LARGE"
        elif exc.status_code == 422:
            error_code = "VALIDATION_ERROR"
        elif exc.status_code >= 500:
            error_code = "SERVER_ERROR"

        content = {
            "success": False,
            "error": {
                "code": error_code,
                "message": str(detail) if not isinstance(detail, dict) else detail.get("message", "An error occurred")
            }
        }

    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom handler for Pydantic validation errors"""
    # For some specific endpoints, we want 400 instead of 422 if it's a missing field
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    # Check if it's a missing file in the extract endpoint (not extract-info)
    if "/documents/extract" in request.url.path and "/documents/extract-info" not in request.url.path:
        for error in exc.errors():
            if error.get("type") == "missing" and ("file" in error.get("loc", []) or "body" in error.get("loc", [])):
                status_code = status.HTTP_400_BAD_REQUEST
                break

    # Format the validation errors into a single message
    error_messages = []
    for error in exc.errors():
        loc = ".".join([str(i) for i in error.get("loc", []) if i != "body"])
        msg = error.get("msg")
        if loc:
            error_messages.append(f"{loc}: {msg}")
        else:
            error_messages.append(msg)

    message = "; ".join(error_messages) if error_messages else "Validation error"

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message
            }
        }
    )


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routes
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(simplification.router, prefix="/api", tags=["simplification"])
app.include_router(extraction.router, prefix="/api", tags=["extraction"])
app.include_router(validation.router, prefix="/api", tags=["validation"])
app.include_router(readability.router, prefix="/api", tags=["documents"])
app.include_router(translation.router, prefix="/api", tags=["translation"])
app.include_router(tts.router, prefix="/api", tags=["translation"])
app.include_router(history.router, prefix="/api", tags=["history"])


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint - redirects to API documentation"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
