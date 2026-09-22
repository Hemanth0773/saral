"""
Information extraction API routes.
Handles structured information extraction endpoints.
"""

from fastapi import APIRouter, HTTPException
import time

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.extraction import ExtractionRequest, ExtractionResponse, StructuredInformation
from app.schemas.document import ErrorResponse
from app.services import extraction_service
from app.services.document_service import generate_document_id

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/documents/extract-info",
    response_model=ExtractionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["extraction"],
    summary="Extract structured information",
    description="""Extract structured information from government documents for cognitive accessibility.

Extracts:
- Document title and summary
- Deadlines and important dates
- Eligibility requirements
- Age requirements
- Required documents
- Monetary amounts
- Percentages and interest rates
- Application procedures
- Important conditions
- Contact information
- Locations and offices
- Organizations and entities

The original document text remains the ultimate source of truth. Extraction uses deterministic pattern matching for critical facts (dates, amounts, percentages) and pattern-based extraction for semantic categories.""",
)
async def extract_structured_information(request: ExtractionRequest) -> dict:
    """
    Extract structured information from government document text.

    Performs deterministic and pattern-based extraction to convert unstructured
    government document text into structured information useful for cognitive accessibility.

    Args:
        request: ExtractionRequest with text and extraction options

    Returns:
        ExtractionResponse with structured information

    Raises:
        HTTPException: If extraction fails or validation fails
    """
    try:
        # Log request details
        text_length = len(request.text)
        logger.info(
            f"Information extraction request: text_length={text_length}, "
            f"extract_title={request.extract_title}, extract_summary={request.extract_summary}"
        )

        # Validate text length
        if text_length > settings.MAX_DOCUMENT_LENGTH:
            logger.warning(f"Text too long: {text_length} > {settings.MAX_DOCUMENT_LENGTH}")
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "TEXT_TOO_LONG",
                        "message": f"Text exceeds maximum length of {settings.MAX_DOCUMENT_LENGTH} characters"
                    }
                }
            )

        # Generate document ID
        document_id = generate_document_id()

        # Measure extraction time
        start_time = time.time()

        try:
            # Extract structured information
            structured_info = extraction_service.extract_structured_information(
                text=request.text,
                extract_title=request.extract_title,
                extract_summary=request.extract_summary
            )

        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": {
                        "code": "EXTRACTION_FAILED",
                        "message": "Structured information extraction failed"
                    }
                }
            )

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Validate critical facts
        validation_results = extraction_service.validate_critical_facts(
            structured_info,
            request.text
        )

        # Build response
        response_data = {
            "success": True,
            "document_id": document_id,
            "original_text": request.text,
            "structured_information": structured_info,
            "extraction_method": "deterministic",
            "processing_time_ms": processing_time_ms,
            "metadata": {
                "facts_preserved": validation_results["facts_extracted"],
                "facts_count": validation_results["critical_facts_count"],
                "extraction_issues": validation_results["issues"]
            }
        }

        logger.info(
            f"Extraction completed successfully: {document_id}, "
            f"processing_time={processing_time_ms}ms, "
            f"facts_count={validation_results['critical_facts_count']}"
        )

        return response_data

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in extract_structured_information: {str(e)}")
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
        logger.error(f"Unexpected error in extract_structured_information: {str(e)}")
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
