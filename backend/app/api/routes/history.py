"""
Document processing history API routes.
Provides endpoints for retrieving previously processed document history.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.schemas.document import ErrorResponse
from app.schemas.history import HistoryListResponse
from app.services import history_service
from app.db.database import get_db

logger = get_logger(__name__)

router = APIRouter()


def get_db_or_error(db: Session = Depends(get_db)):
    """
    Wrapper that handles database dependency failures gracefully.
    """
    return db


@router.get(
    "/history",
    response_model=HistoryListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid pagination parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
    },
    tags=["history"],
    summary="List document processing history",
    description="""Retrieve paginated list of previously processed documents.

    Returns documents ordered by most recent processing time.
    Each record contains metadata from the processing pipeline including
    document ID, filename, language, readability scores, simplified text,
    and validation status.

    **Pagination**
    - `page`: Page number, minimum 1 (default: 1)
    - `limit`: Items per page, between 1 and 50 (default: 10)

    Database must be enabled (USE_DATABASE=true) and properly configured
    for this endpoint to function.
    """,
)
async def list_history(
    page: int = Query(default=1, ge=1, description="Page number (minimum: 1)"),
    limit: int = Query(default=10, ge=1, le=50, description="Items per page (1-50)"),
    db: Session = Depends(get_db),
):
    """
    List document processing history with pagination.

    Args:
        page: Page number (1-based)
        limit: Number of items per page
        db: Database session

    Returns:
        HistoryListResponse with paginated history records

    Raises:
        HTTPException: If database is unavailable or query fails
    """
    try:
        logger.info(f"History list request: page={page}, limit={limit}")

        result = history_service.list_history(db, page=page, limit=limit)

        items = [history_service.serialize_history_record(record) for record in result["items"]]

        response_data = {
            "success": True,
            "items": items,
            "page": result["page"],
            "limit": result["limit"],
            "total": result["total"],
            "total_pages": result["total_pages"],
        }

        logger.info(f"History list returned {len(items)} records (total={result['total']})")
        return response_data

    except history_service.DatabaseError as e:
        logger.error(f"Database error in list_history: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Unable to access document history."
                }
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in list_history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "HISTORY_LIST_FAILED",
                    "message": "An unexpected error occurred while retrieving history."
                }
            }
        )


@router.get(
    "/history/{document_id}",
    response_model=None,
    responses={
        404: {"model": ErrorResponse, "description": "Document history not found"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["history"],
    summary="Get document history by document ID",
    description="""Retrieve processing history for a specific document.

    Since a document may be processed multiple times (e.g., with different
    languages, grade levels, or settings), this endpoint returns all history
    records for the given document_id, ordered newest first.

    Each record contains the full processing metadata including:
    - Document ID, filename, processing status
    - Original and target languages
    - Readability metrics (original and simplified grade levels)
    - Simplified text output
    - Validation results and warnings
    - Timestamps

    Database must be enabled (USE_DATABASE=true) and properly configured
    for this endpoint to function.
    """,
)
async def get_history(
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve history for a specific document ID.

    Args:
        document_id: Document ID to look up (format: doc_xxx)
        db: Database session

    Returns:
        HistoryResponse with history record(s) for the document

    Raises:
        HTTPException: 404 if not found, 503 if database unavailable
    """
    try:
        logger.info(f"History lookup request for document_id: {document_id}")

        records = history_service.get_history_by_document_id(db, document_id)

        if not records:
            logger.info(f"No history found for document_id: {document_id}")
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {
                        "code": "HISTORY_NOT_FOUND",
                        "message": f"No history found for document ID: {document_id}"
                    }
                }
            )

        # Return all records for this document_id (may be multiple if re-processed)
        items = [history_service.serialize_history_record(record) for record in records]

        # Primary response is the most recent record
        primary = items[0]

        response_data = {
            "success": True,
            "history": primary,
            "all_records": items if len(items) > 1 else None,
            "total_records": len(items),
        }

        logger.info(f"History lookup returned {len(items)} records for document_id: {document_id}")
        return response_data

    except HTTPException:
        raise
    except history_service.DatabaseError as e:
        logger.error(f"Database error in get_history: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Unable to access document history."
                }
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "HISTORY_LOOKUP_FAILED",
                    "message": "An unexpected error occurred while retrieving document history."
                }
            }
        )
