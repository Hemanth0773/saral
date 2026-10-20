"""
Simplification API routes.
Handles LLM-based text simplification endpoints.
"""

import asyncio

from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.simplification import SimplificationRequest, SimplificationResponse
from app.schemas.document import ErrorResponse
from app.services import llm_service, validation_service
from app.services import extraction_service, summary_service
from app.services.document_service import generate_document_id

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/documents/simplify",
    response_model=SimplificationResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        503: {"model": ErrorResponse, "description": "LLM service unavailable"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["documents"],
    summary="Simplify text using LLM",
    description="""Simplify complex government document text to make it more accessible while preserving all critical factual information.

CRITICAL PRESERVATION REQUIREMENTS:
- All dates, deadlines, and time frames
- All monetary amounts (especially ₹ amounts)
- All percentages
- All ages and age requirements
- All quantities and numerical values
- All eligibility requirements
- All required documents
- All important conditions and exceptions
- All contact information (if present)

The simplification aims for the specified reading grade level (default: 5) while maintaining original meaning and facts.""",
)
async def simplify_document(request: SimplificationRequest) -> dict:
    """
    Simplify government document text using LLM.

    Performs language simplification while preserving all critical factual information:
    - Dates, deadlines, time frames
    - Monetary amounts (including ₹)
    - Percentages
    - Ages and age requirements
    - Quantities and numerical values
    - Eligibility requirements
    - Required documents
    - Important conditions and exceptions
    - Contact information (if present)

    Args:
        request: SimplificationRequest with text and target grade level

    Returns:
        SimplificationResponse with simplified text and validation results

    Raises:
        HTTPException: If simplification fails or validation fails
    """
    try:
        # Log request details
        text_length = len(request.text)
        logger.info(
            f"Simplification request: target_grade_level={request.target_grade_level}, "
            f"text_length={text_length}"
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

        # Perform simplification
        try:
            # Generate simplification response.
            #
            # The provider calls and the retry backoff are blocking, so the
            # work is handed to a worker thread. That keeps the FastAPI event
            # loop free while a large document is simplified and while the
            # backend waits for a rate limit window to reset.
            response_data = await asyncio.to_thread(
                llm_service.generate_simplification_response,
                text=request.text,
                target_grade_level=request.target_grade_level,
                document_id=document_id
            )

        except llm_service.LLMQuotaExhaustedError as e:
            logger.error(f"LLM quota exhausted: {str(e)}")
            raise HTTPException(
                status_code=429,
                detail={
                    "success": False,
                    "error": {
                        "code": "LLM_QUOTA_EXHAUSTED",
                        "message": "API quota exhausted. Please try again later."
                    }
                }
            )
        except llm_service.LLMAuthenticationError as e:
            logger.error(f"LLM authentication error: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail={
                    "success": False,
                    "error": {
                        "code": "LLM_AUTHENTICATION_ERROR",
                        "message": "LLM service authentication failed. Please check configuration."
                    }
                }
            )
        except llm_service.LLMRateLimitError as e:
            logger.error(f"LLM rate limited: {str(e)}")
            raise HTTPException(
                status_code=429,
                detail={
                    "success": False,
                    "error": {
                        "code": "LLM_RATE_LIMITED",
                        "message": "LLM service rate limit exceeded. Please try again in a moment."
                    }
                }
            )
        except llm_service.LLMTransientError as e:
            # Every provider was temporarily unavailable (overloaded, 5xx, ...)
            logger.error(f"LLM service temporarily unavailable: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail={
                    "success": False,
                    "error": {
                        "code": "LLM_SERVICE_UNAVAILABLE",
                        "message": "The simplification service is temporarily busy. Please try again in a moment."
                    }
                }
            )
        except llm_service.LLMServiceError as e:
            # Check if it's a configuration error
            error_str = str(e).lower()
            if "api key" in error_str or "not configured" in error_str:
                logger.error(f"LLM configuration error: {str(e)}")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "success": False,
                        "error": {
                            "code": "LLM_CONFIGURATION_ERROR",
                            "message": "LLM service not properly configured. Please check LLM_API_KEY."
                        }
                    }
                )
            elif "timeout" in error_str:
                logger.error(f"LLM timeout: {str(e)}")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "success": False,
                        "error": {
                            "code": "LLM_TIMEOUT",
                            "message": "LLM service timeout. Please try again."
                        }
                    }
                )
            else:
                logger.error(f"LLM service error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "success": False,
                        "error": {
                            "code": "SIMPLIFICATION_FAILED",
                            "message": "Text simplification failed. Please try again."
                        }
                    }
                )

        # Validate fact preservation
        response_data = validation_service.validate_final_response(response_data)

        # Build the canonical Instant Summary. The website and the Chrome
        # extension render this same list, so the two interfaces cannot show
        # different facts for the same document. It is derived from the
        # structured extraction of the source text, not from the model output.
        try:
            structured_info = extraction_service.extract_structured_information(
                text=request.text,
                extract_title=False,
                extract_summary=False,
            )
            summary = summary_service.build_instant_summary(
                structured_info,
                response_data.get("preserved_facts"),
            )
            response_data["instant_summary"] = summary["items"]
            response_data.setdefault("metadata", {})["summary_total"] = summary["total"]
            response_data["metadata"]["summary_hidden"] = summary["hidden"]
        except Exception as summary_error:
            # The summary is an addition, never a reason to fail a
            # simplification that already succeeded.
            logger.warning(f"Could not build the instant summary: {str(summary_error)}")
            response_data["instant_summary"] = []

        # Check validation results
        if not response_data["validation_passed"]:
            logger.warning(
                f"Simplification validation failed: {response_data['validation_failures']}"
            )
            # We still return the result but mark validation as failed
            # This allows the client to decide what to do

        logger.info(
            f"Simplification completed successfully: {document_id}, "
            f"processing_time={response_data['processing_time_ms']}ms, "
            f"validation_passed={response_data['validation_passed']}"
        )

        # Record processing history if database is enabled
        if settings.USE_DATABASE:
            try:
                from app.db.database import SessionLocal
                from app.services import history_service

                db_session = SessionLocal()
                try:
                    validation_warnings = None
                    if not response_data["validation_passed"]:
                        validation_warnings = [
                            {"message": msg} for msg in response_data.get("validation_failures", [])
                        ]

                    history_service.record_history(
                        db=db_session,
                        document_id=document_id,
                        processing_status="completed",
                        original_language="en",
                        selected_language="en",
                        readability_target_grade=float(request.target_grade_level),
                        simplified_text=response_data.get("simplified_text"),
                        validation_status="PASS" if response_data["validation_passed"] else "FAIL",
                        validation_warnings=validation_warnings,
                        processing_time_ms=response_data.get("processing_time_ms"),
                        text_length=len(request.text),
                    )
                finally:
                    db_session.close()
            except Exception as db_error:
                logger.warning(f"Failed to record history for document_id={document_id}: {str(db_error)}")

        return response_data

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in simplify_document: {str(e)}")
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
        logger.error(f"Unexpected error in simplify_document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "SIMPLIFICATION_FAILED",
                    "message": "An unexpected error occurred during simplification"
                }
            }
        )


@router.post(
    "/documents/simplify/validate",
    response_model=dict,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["documents"],
    summary="Validate fact preservation",
    description="Validate that critical factual information is preserved between original and simplified text.",
)
async def validate_simplification(original_text: str, simplified_text: str) -> dict:
    """
    Validate fact preservation between original and simplified text.

    Args:
        original_text: Original text
        simplified_text: Simplified text to validate

    Returns:
        Dictionary with validation results

    Raises:
        HTTPException: If validation fails
    """
    try:
        # Validate inputs
        if not original_text or not original_text.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": "Original text cannot be empty"
                    }
                }
            )

        if not simplified_text or not simplified_text.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": "Simplified text cannot be empty"
                    }
                }
            )

        # Perform validation
        preserved_facts, validation_failures = validation_service.validate_fact_preservation(
            original_text, simplified_text
        )

        # Calculate statistics
        total_facts = len(preserved_facts)
        preserved_count = sum(1 for fact in preserved_facts if fact.preserved_in_simplified)

        return {
            "success": True,
            "validation_passed": len(validation_failures) == 0,
            "preserved_facts": preserved_facts,
            "validation_failures": validation_failures,
            "statistics": {
                "total_facts": total_facts,
                "preserved_facts": preserved_count,
                "preservation_rate": preserved_count / total_facts if total_facts > 0 else 1.0
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in validate_simplification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "An unexpected error occurred during validation"
                }
            }
        )
