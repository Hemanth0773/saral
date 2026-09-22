"""
M7 Advanced Fact Validation API routes.
Handles cross-document fact validation endpoints.
"""

from fastapi import APIRouter, HTTPException
import time

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.validation import (
    CrossDocumentValidationRequest,
    CrossDocumentValidationResult,
)
from app.schemas.document import ErrorResponse
from app.services import advanced_validation_service

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/documents/validate",
    response_model=CrossDocumentValidationResult,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["validation"],
    summary="Cross-validate facts across documents",
    description="""Validate that facts are consistent across original, simplified (M5), and structured (M6) documents.

The original document is always the source of truth.

Validates:
- Dates and deadlines (format normalization)
- Monetary amounts (currency normalization)
- Percentages
- Ages and age requirements
- Quantities
- Required documents
- Eligibility requirements
- Important conditions

Returns detailed validation results with contradictions if any facts changed or were omitted.""",
)
async def validate_cross_document(request: CrossDocumentValidationRequest) -> dict:
    """
    Validate facts across original, simplified, and structured documents.

    Original text is always the source of truth. Simplified text (M5) and
    structured information (M6) are validated against the original.

    Args:
        request: CrossDocumentValidationRequest with original, simplified, and structured texts

    Returns:
        CrossDocumentValidationResult with detailed validation information

    Raises:
        HTTPException: If validation request is invalid
    """
    try:
        # Log request details
        logger.info(
            f"Cross-document validation request: "
            f"original_length={len(request.original_text)}, "
            f"has_simplified={request.simplified_text is not None}, "
            f"has_structured={request.structured_information is not None}"
        )

        # Validate original text is not empty
        if not request.original_text or not request.original_text.strip():
            logger.warning("Original text cannot be empty")
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": "Original text cannot be empty",
                    },
                },
            )

        # Validate text length
        if len(request.original_text) > settings.MAX_DOCUMENT_LENGTH:
            logger.warning(
                f"Original text too long: {len(request.original_text)} > {settings.MAX_DOCUMENT_LENGTH}"
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "TEXT_TOO_LONG",
                        "message": f"Original text exceeds maximum length of {settings.MAX_DOCUMENT_LENGTH} characters",
                    },
                },
            )

        if (
            request.simplified_text
            and len(request.simplified_text) > settings.MAX_DOCUMENT_LENGTH
        ):
            logger.warning(
                f"Simplified text too long: {len(request.simplified_text)} > {settings.MAX_DOCUMENT_LENGTH}"
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "TEXT_TOO_LONG",
                        "message": f"Simplified text exceeds maximum length of {settings.MAX_DOCUMENT_LENGTH} characters",
                    },
                },
            )

        # Perform validation
        result = advanced_validation_service.validate_cross_document(
            original_text=request.original_text,
            simplified_text=request.simplified_text,
            structured_information=request.structured_information,
        )

        # Log result
        advanced_validation_service.log_validation_result(result)

        logger.info(
            f"Cross-document validation completed: "
            f"validation_passed={result.validation_passed}, "
            f"contradictions={len(result.contradictions)}"
        )

        return result.model_dump()

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
                    "message": str(e),
                },
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error in validate_cross_document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "An unexpected error occurred during validation",
                },
            },
        )
