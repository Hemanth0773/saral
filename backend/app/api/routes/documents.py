"""
Document extraction API routes.
Handles file uploads and URL extraction endpoints.
"""

from fastapi import APIRouter, File, UploadFile, Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.security import validate_file_upload, validate_url
from app.core.logging import get_logger
from app.schemas.document import (
    DocumentExtractResponse,
    URLExtractRequest,
    URLExtractResponse,
    ErrorResponse,
)
from app.services import document_service

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/documents/extract",
    response_model=DocumentExtractResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        413: {"model": ErrorResponse, "description": "File too large"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["documents"],
    summary="Extract text from uploaded document",
    description="Upload a PDF, TXT, DOCX, or image file to extract text. Supports government documents.",
)
async def extract_document(file: UploadFile = File(...)) -> dict:
    """
    Extract text from uploaded document file.

    Supports:
    - PDF files (.pdf)
    - Text files (.txt)
    - Word documents (.docx, .doc)
    - Images (.jpg, .jpeg, .png)

    Args:
        file: Uploaded file

    Returns:
        DocumentExtractResponse with extracted text and metadata

    Raises:
        HTTPException: If validation fails or processing fails
    """
    if not file:
        logger.warning("No file provided in extract request")
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename:
        logger.warning("File has no filename")
        raise HTTPException(status_code=400, detail="File must have a filename")

    try:
        # Read file content
        file_content = await file.read()
        file_size_bytes = len(file_content)

        logger.info(f"Extract request: {file.filename} ({file_size_bytes} bytes)")

        # Validate file
        is_valid, error_message = validate_file_upload(
            filename=file.filename,
            file_size_bytes=file_size_bytes,
            max_file_size_mb=settings.MAX_FILE_SIZE_MB,
        )

        if not is_valid:
            logger.warning(f"File validation failed: {error_message}")
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_FILE_TYPE",
                        "message": error_message
                    }
                }
            )

        # Process file
        result = document_service.process_pdf_upload(
            file_content=file_content,
            original_filename=file.filename,
            upload_dir=settings.UPLOAD_DIRECTORY,
        )

        logger.info(f"Document extracted successfully: {result['document_id']}")
        return result

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(e)
                }
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in extract_document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": "An unexpected error occurred during extraction"
                }
            }
        )


@router.post(
    "/documents/url",
    response_model=URLExtractResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["documents"],
    summary="Extract text from government webpage",
    description="Provide a government website URL to extract text content.",
)
async def extract_from_url(request: URLExtractRequest) -> dict:
    """
    Extract text from a government webpage URL.

    Args:
        request: URLExtractRequest with URL parameter

    Returns:
        URLExtractResponse with extracted text and metadata

    Raises:
        HTTPException: If URL is invalid or processing fails
    """
    if not request.url:
        logger.warning("No URL provided in request")
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        logger.info(f"URL extract request: {request.url}")

        # Validate URL
        is_valid, error_message = validate_url(request.url)

        if not is_valid:
            logger.warning(f"URL validation failed: {error_message}")
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_URL",
                        "message": error_message
                    }
                }
            )

        # Process URL
        result = document_service.process_url_input(request.url)

        logger.info(f"URL extracted successfully: {result['document_id']}")
        return result

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"URL processing error: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": str(e)
                }
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in extract_from_url: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": "An unexpected error occurred during extraction"
                }
            }
        )
