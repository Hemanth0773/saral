"""
Readability analysis API routes.
Handles readability analysis and comparison endpoints.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.core.logging import get_logger
from app.schemas.readability import (
    ReadabilityAnalysisRequest,
    ReadabilityAnalysisResponse,
)
from app.schemas.document import ErrorResponse
from app.services import readability_service
from app.utils import text_utils

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/documents/readability",
    response_model=ReadabilityAnalysisResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["documents"],
    summary="Analyze readability metrics",
    description="""Analyze and compare readability metrics between original and simplified text.

Provides objective readability measurements including:
- Flesch Reading Ease (0-100 scale)
- Flesch-Kincaid Grade Level (US grade 1-12+)
- Word, sentence, and syllable counts
- Average sentence length
- Readability improvements

Readability analysis is deterministic and does NOT measure cognitive accessibility alone.
Use in conjunction with M7 fact validation to ensure document quality.""",
)
async def analyze_readability(request: ReadabilityAnalysisRequest) -> dict:
    """
    Analyze readability of original vs simplified text.

    Args:
        request: ReadabilityAnalysisRequest with original_text, simplified_text, target_grade_level

    Returns:
        ReadabilityAnalysisResponse with metrics and comparison

    Raises:
        HTTPException: If analysis fails
    """
    try:
        # Validate input
        if not request.original_text or not request.original_text.strip():
            raise HTTPException(
                status_code=400,
                detail="original_text cannot be empty"
            )

        if not request.simplified_text or not request.simplified_text.strip():
            raise HTTPException(
                status_code=400,
                detail="simplified_text cannot be empty"
            )

        # Detect language
        language = text_utils.detect_language_heuristic(request.original_text)

        # Currently only English is fully supported
        supported = (language == "en")

        if not supported:
            logger.info(f"Readability analysis requested for unsupported language: {language}")
            return ReadabilityAnalysisResponse(
                success=True,
                supported=False,
                message=f"Readability metrics are currently supported for English text only (detected: {language}).",
                processing_time_ms=0,
                language=language,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

        # Perform readability analysis
        analysis_result = readability_service.compare_readability(
            original_text=request.original_text,
            simplified_text=request.simplified_text,
            target_grade_level=request.target_grade_level,
        )

        response = ReadabilityAnalysisResponse(
            success=True,
            supported=True,
            original=analysis_result["original"],
            simplified=analysis_result["simplified"],
            comparison=analysis_result["comparison"],
            processing_time_ms=analysis_result["processing_time_ms"],
            language=language,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        logger.info(
            f"Readability analysis completed: "
            f"original_grade={analysis_result['original']['flesch_kincaid_grade']}, "
            f"simplified_grade={analysis_result['simplified']['flesch_kincaid_grade']}, "
            f"target_achieved={analysis_result['comparison']['target_achieved']}"
        )

        return response

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Readability analysis validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Readability analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Readability analysis failed: {str(e)}"
        )
