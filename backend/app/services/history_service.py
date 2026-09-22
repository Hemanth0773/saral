"""
History service for document processing history.
Provides CRUD operations for DocumentHistory records.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.logging import get_logger
from app.db.models import DocumentHistory

logger = get_logger(__name__)


class HistoryServiceError(Exception):
    """Base exception for history service errors"""
    pass


class DatabaseError(HistoryServiceError):
    """Exception raised when database operations fail"""
    pass


def generate_history_id() -> str:
    """Generate a unique UUID for history records."""
    return uuid.uuid4().hex


def record_history(
    db: Session,
    document_id: str,
    filename: Optional[str] = None,
    processing_status: str = "completed",
    original_language: str = "en",
    selected_language: Optional[str] = None,
    readability_original_grade: Optional[float] = None,
    readability_simplified_grade: Optional[float] = None,
    readability_target_grade: Optional[float] = None,
    readability_target_achieved: Optional[bool] = None,
    simplified_text: Optional[str] = None,
    validation_status: Optional[str] = None,
    validation_warnings: Optional[List[Dict[str, Any]]] = None,
    processing_time_ms: Optional[int] = None,
    text_length: Optional[int] = None,
    word_count: Optional[int] = None,
) -> DocumentHistory:
    """
    Create a new document history record.

    Args:
        db: SQLAlchemy session
        document_id: Application document ID (doc_xxx format)
        filename: Original uploaded filename
        processing_status: completed, failed, partial
        original_language: Detected original language
        selected_language: Language used for output
        readability_original_grade: FK grade of original text (M8)
        readability_simplified_grade: FK grade of simplified text (M8)
        readability_target_grade: Target grade level (M8)
        readability_target_achieved: Whether target was achieved (M8)
        simplified_text: Simplified text output (M5)
        validation_status: PASS, FAIL, WARNING, INCONCLUSIVE (M7)
        validation_warnings: Structured validation warnings (M7)
        processing_time_ms: Total processing time
        text_length: Character length of original text
        word_count: Word count of original text

    Returns:
        Created DocumentHistory record

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        history_id = generate_history_id()
        now = datetime.now(timezone.utc)

        record = DocumentHistory(
            id=history_id,
            document_id=document_id,
            filename=filename,
            processing_status=processing_status,
            original_language=original_language,
            selected_language=selected_language,
            readability_original_grade=readability_original_grade,
            readability_simplified_grade=readability_simplified_grade,
            readability_target_grade=readability_target_grade,
            readability_target_achieved=readability_target_achieved,
            simplified_text=simplified_text,
            validation_status=validation_status,
            validation_warnings=validation_warnings,
            processing_time_ms=processing_time_ms,
            text_length=text_length,
            word_count=word_count,
            created_at=now,
            updated_at=now,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(f"History record created: id={history_id}, document_id={document_id}")
        return record

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create history record for document_id={document_id}: {str(e)}")
        raise DatabaseError(f"Failed to create history record: {str(e)}")


def get_history_by_id(
    db: Session,
    history_id: str
) -> Optional[DocumentHistory]:
    """
    Retrieve a single history record by its UUID.

    Args:
        db: SQLAlchemy session
        history_id: History record UUID

    Returns:
        DocumentHistory record or None if not found

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        record = db.query(DocumentHistory).filter(DocumentHistory.id == history_id).first()
        return record
    except Exception as e:
        logger.error(f"Failed to retrieve history record id={history_id}: {str(e)}")
        raise DatabaseError(f"Failed to retrieve history record: {str(e)}")


def get_history_by_document_id(
    db: Session,
    document_id: str
) -> List[DocumentHistory]:
    """
    Retrieve history records for a specific document_id.

    Since a document can be processed multiple times, this returns
    all matching records ordered by created_at DESC.

    Args:
        db: SQLAlchemy session
        document_id: Application document ID

    Returns:
        List of matching DocumentHistory records (newest first)

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        records = (
            db.query(DocumentHistory)
            .filter(DocumentHistory.document_id == document_id)
            .order_by(DocumentHistory.created_at.desc())
            .all()
        )
        return records
    except Exception as e:
        logger.error(f"Failed to retrieve history for document_id={document_id}: {str(e)}")
        raise DatabaseError(f"Failed to retrieve history: {str(e)}")


def list_history(
    db: Session,
    page: int = 1,
    limit: int = 10
) -> Dict[str, Any]:
    """
    List history records with pagination.

    Args:
        db: SQLAlchemy session
        page: Page number (1-based), >= 1
        limit: Items per page, clamped to 1-50

    Returns:
        Dictionary with items list and pagination metadata

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        # Clamp pagination values
        page = max(1, page)
        limit = max(1, min(50, limit))
        offset = (page - 1) * limit

        # Get total count
        total = db.query(func.count(DocumentHistory.id)).scalar()

        # Get paginated records
        records = (
            db.query(DocumentHistory)
            .order_by(DocumentHistory.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        total_pages = (total + limit - 1) // limit if limit > 0 else 0

        return {
            "items": records,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Failed to list history records: {str(e)}")
        raise DatabaseError(f"Failed to list history: {str(e)}")


def update_processing_status(
    db: Session,
    document_id: str,
    status: str,
    update_all: bool = False,
    history_id: Optional[str] = None
) -> Optional[DocumentHistory]:
    """
    Update processing status of a history record.

    Args:
        db: SQLAlchemy session
        document_id: Application document ID
        status: New processing status
        update_all: If True, update all records with this document_id;
                    if False, update only the most recent (or specified by history_id)
        history_id: Specific history record ID to update (used when update_all=False)

    Returns:
        Updated record or None if not found

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        if history_id:
            record = db.query(DocumentHistory).filter(DocumentHistory.id == history_id).first()
        elif update_all:
            records = db.query(DocumentHistory).filter(DocumentHistory.document_id == document_id).all()
            for record in records:
                record.processing_status = status
                record.updated_at = datetime.now(timezone.utc)
            db.commit()
            return records[0] if records else None
        else:
            record = (
                db.query(DocumentHistory)
                .filter(DocumentHistory.document_id == document_id)
                .order_by(DocumentHistory.created_at.desc())
                .first()
            )

        if record is None:
            return None

        record.processing_status = status
        record.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(record)

        logger.info(f"Updated history record {record.id} status to: {status}")
        return record

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update processing status for document_id={document_id}: {str(e)}")
        raise DatabaseError(f"Failed to update processing status: {str(e)}")


def delete_history_by_document_id(
    db: Session,
    document_id: str
) -> int:
    """
    Delete all history records for a document_id.

    Args:
        db: SQLAlchemy session
        document_id: Application document ID

    Returns:
        Number of deleted records

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        deleted_count = (
            db.query(DocumentHistory)
            .filter(DocumentHistory.document_id == document_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(f"Deleted {deleted_count} history records for document_id={document_id}")
        return deleted_count
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete history for document_id={document_id}: {str(e)}")
        raise DatabaseError(f"Failed to delete history: {str(e)}")


def serialize_history_record(record: DocumentHistory) -> Dict[str, Any]:
    """
    Convert a DocumentHistory model instance to a serializable dictionary.

    Args:
        record: DocumentHistory model instance

    Returns:
        Serializable dictionary with nested readability and validation info
    """
    def convert_datetime(dt):
        if dt is None:
            return None
        if isinstance(dt, str):
            return dt
        return dt.isoformat()

    return {
        "id": record.id,
        "document_id": record.document_id,
        "filename": record.filename,
        "processing_status": record.processing_status,
        "original_language": record.original_language,
        "selected_language": record.selected_language,
        "readability": {
            "original_grade": record.readability_original_grade,
            "simplified_grade": record.readability_simplified_grade,
            "target_grade": record.readability_target_grade,
            "target_achieved": record.readability_target_achieved,
        },
        "simplified_text": record.simplified_text,
        "validation": {
            "status": record.validation_status,
            "warnings": record.validation_warnings,
        },
        "processing_time_ms": record.processing_time_ms,
        "text_length": record.text_length,
        "word_count": record.word_count,
        "created_at": convert_datetime(record.created_at),
        "updated_at": convert_datetime(record.updated_at),
    }
