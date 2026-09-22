"""
SQLAlchemy database models for document processing history.
"""

from sqlalchemy import Column, String, Text, Boolean, Float, DateTime, JSON, Index
from datetime import datetime, timezone
from app.db.database import Base


class DocumentHistory(Base):
    """
    Document processing history record.

    Stores metadata from the document simplification pipeline
    (Milestones 5-10) for retrieval via the History API.

    A document_id is NOT unique — the same document can be
    processed multiple times with different settings, each
    generating a separate history record.
    """
    __tablename__ = "document_history"

    # Primary key
    id = Column(String(36), primary_key=True, comment="UUID primary key")

    # Document identifiers
    document_id = Column(String(64), nullable=False, index=True, comment="Application document ID (doc_xxx format)")
    filename = Column(String(255), nullable=True, comment="Original uploaded filename if applicable")

    # Processing status
    processing_status = Column(String(50), nullable=False, default="completed", comment="Processing status: completed, failed, partial")

    # Language settings
    original_language = Column(String(10), nullable=True, default="en", comment="Detected original language")
    selected_language = Column(String(10), nullable=True, comment="Language used for output (translation/simplification)")

    # Readability information (from M8)
    readability_original_grade = Column(Float, nullable=True, comment="Flesch-Kincaid grade level of original text")
    readability_simplified_grade = Column(Float, nullable=True, comment="Flesch-Kincaid grade level of simplified text")
    readability_target_grade = Column(Float, nullable=True, comment="Target grade level requested")
    readability_target_achieved = Column(Boolean, default=False, comment="Whether simplified text meets target grade level")

    # Simplified output (from M5)
    simplified_text = Column(Text, nullable=True, comment="Simplified text output")

    # Validation result (from M7)
    validation_status = Column(String(50), nullable=True, comment="PASS, FAIL, WARNING, or INCONCLUSIVE")
    validation_warnings = Column(JSON, nullable=True, comment="Structured validation warnings/contradictions")

    # Processing metadata
    processing_time_ms = Column(Float, nullable=True, comment="Total processing time in milliseconds")
    text_length = Column(Float, nullable=True, comment="Character length of original text")
    word_count = Column(Float, nullable=True, comment="Word count of original text")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Last update timestamp")

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_document_history_document_id", "document_id"),
        Index("idx_document_history_created_at", "created_at"),
        Index("idx_document_history_processing_status", "processing_status"),
        Index("idx_document_history_original_language", "original_language"),
    )
