"""
Document extraction API routes.
Handles file uploads and URL extraction endpoints.
"""

from fastapi import APIRouter, File, UploadFile, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.security import validate_file_upload, validate_url
from app.core.logging import get_logger
from app.schemas.document import (
    DocumentExtractResponse,
    URLExtractRequest,
    URLExtractResponse,
    ErrorResponse,
)
from app.schemas.nlp import NLPProcessingResponse
from app.services import document_service, nlp_service

logger = get_logger(__name__)

router = APIRouter()


class TextInput(BaseModel):
    """Request model for NLP preprocessing"""
    text: str = Field(..., min_length=1, description="Text to preprocess with NLP")


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
        result = document_service.process_document_upload(
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


@router.post(
    "/documents/preprocess",
    response_model=NLPProcessingResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        503: {"model": ErrorResponse, "description": "NLP model unavailable"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["documents"],
    summary="Preprocess extracted text with NLP",
    description="Apply NLP preprocessing (normalization, sentence segmentation, tokenization, entity extraction) to extracted text.",
)
async def preprocess_document(request: TextInput) -> dict:
    """
    Apply NLP preprocessing to extracted document text.

    Performs comprehensive linguistic analysis including:
    - Text normalization and cleaning
    - Sentence tokenization
    - Named entity recognition (NER)
    - Part-of-speech (POS) tagging
    - Key phrase extraction

    Args:
        request: TextInput with text to preprocess

    Returns:
        NLPProcessingResponse with linguistic analysis

    Raises:
        HTTPException: If preprocessing fails or model unavailable
    """
    if not request.text or not request.text.strip():
        logger.warning("Empty text provided for preprocessing")
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "Text cannot be empty"
                }
            }
        )

    try:
        logger.info(f"NLP preprocessing request for text of length {len(request.text)}")
        result = nlp_service.preprocess_text(request.text)
        logger.info(f"NLP preprocessing completed successfully: {result.document_id}")
        return result

    except ValueError as e:
        # Handle case where spaCy model is not loaded or text is invalid
        logger.error(f"NLP preprocessing validation error: {str(e)}")

        # Check if this is a model loading error
        if "model" in str(e).lower() or "not found" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail={
                    "success": False,
                    "error": {
                        "code": "NLP_MODEL_UNAVAILABLE",
                        "message": str(e)
                    }
                }
            )
        else:
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
        logger.error(f"Unexpected error in preprocess_document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "PREPROCESSING_FAILED",
                    "message": "An unexpected error occurred during preprocessing"
                }
            }
        )
