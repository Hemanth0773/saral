"""
Pydantic schemas for document processing history.
Used for request/response validation of history endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ReadabilityInfo(BaseModel):
    """Readability information from M8"""
    original_grade: Optional[float] = Field(None, description="Flesch-Kincaid grade level of original text")
    simplified_grade: Optional[float] = Field(None, description="Flesch-Kincaid grade level of simplified text")
    target_grade: Optional[float] = Field(None, description="Target grade level requested")
    target_achieved: bool = Field(default=False, description="Whether simplified text meets target grade level")


class ValidationInfo(BaseModel):
    """Validation result from M7"""
    status: Optional[str] = Field(None, description="PASS, FAIL, WARNING, or INCONCLUSIVE")
    warnings: Optional[List[Dict[str, Any]]] = Field(default=None, description="Structured validation warnings/contradictions")
    facts_checked: Optional[int] = Field(None, description="Total number of facts checked")
    facts_preserved: Optional[int] = Field(None, description="Number of facts correctly preserved")


class HistoryResponse(BaseModel):
    """Response schema for a single history record"""
    success: bool = Field(default=True, description="Whether the request was successful")
    history: Dict[str, Any] = Field(..., description="History record data")


class HistoryListResponse(BaseModel):
    """Response schema for paginated history list"""
    success: bool = Field(default=True, description="Whether the request was successful")
    items: List[Dict[str, Any]] = Field(..., description="List of history records")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total number of records")
    total_pages: int = Field(..., description="Total number of pages")


class ProcessingStatusUpdate(BaseModel):
    """Request schema for updating processing status"""
    processing_status: str = Field(..., description="Processing status: completed, failed, partial")


class HistoryError(BaseModel):
    """Error response for history endpoints"""
    success: bool = Field(default=False, description="Whether the operation was successful")
    error: Dict[str, str] = Field(..., description="Error details with code and message")
