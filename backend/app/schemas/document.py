"""
Pydantic schemas for document processing.
Used for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Metadata about extracted document"""
    document_id: str = Field(..., description="Unique document identifier")
    filename: Optional[str] = Field(None, description="Original filename if from file upload")
    language: str = Field(default="en", description="Detected language (ISO 639-1 code)")
    page_count: int = Field(default=1, description="Number of pages (estimated for web)")
    word_count: int = Field(default=0, description="Number of words in extracted text")
    extraction_method: str = Field(..., description="Method used: pdf_text, pdf_image_stub, webpage")
    extracted_at: str = Field(..., description="ISO 8601 timestamp of extraction")


class DocumentExtractResponse(BaseModel):
    """Response from file upload extraction endpoint"""
    success: bool = Field(default=True, description="Whether extraction was successful")
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    language: str = Field(default="en", description="Detected language")
    page_count: int = Field(default=1, description="Number of pages")
    extraction_method: str = Field(..., description="Extraction method used")
    text: str = Field(..., description="Extracted text (truncated to 50000 chars if longer)")
    text_truncated: bool = Field(default=False, description="Whether text was truncated")
    metadata: DocumentMetadata = Field(..., description="Document metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "doc_20260918_135844_a1b2c3d4",
                "filename": "scheme.pdf",
                "language": "en",
                "page_count": 5,
                "extraction_method": "pdf_text",
                "text": "Government Scheme for Housing Assistance...",
                "text_truncated": False,
                "metadata": {
                    "document_id": "doc_20260918_135844_a1b2c3d4",
                    "filename": "scheme.pdf",
                    "language": "en",
                    "page_count": 5,
                    "word_count": 1200,
                    "extraction_method": "pdf_text",
                    "extracted_at": "2026-09-18T13:58:44.672Z"
                }
            }
        }


class URLExtractRequest(BaseModel):
    """Request to extract text from URL"""
    url: str = Field(..., description="URL to extract text from (must be http/https)")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.gov.in/scheme/housing-assistance"
            }
        }


class URLExtractResponse(BaseModel):
    """Response from URL extraction endpoint"""
    success: bool = Field(default=True, description="Whether extraction was successful")
    document_id: str = Field(..., description="Unique document identifier")
    language: str = Field(default="en", description="Detected language")
    extraction_method: str = Field(default="webpage", description="Extraction method")
    text: str = Field(..., description="Extracted text (truncated to 50000 chars if longer)")
    text_truncated: bool = Field(default=False, description="Whether text was truncated")
    source_url: str = Field(..., description="URL that was processed")
    metadata: DocumentMetadata = Field(..., description="Document metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "doc_20260918_135844_b2c3d4e5",
                "language": "en",
                "extraction_method": "webpage",
                "text": "Government Scheme for Housing Assistance...",
                "text_truncated": False,
                "source_url": "https://example.gov.in/scheme/housing-assistance",
                "metadata": {
                    "document_id": "doc_20260918_135844_b2c3d4e5",
                    "filename": None,
                    "language": "en",
                    "page_count": 1,
                    "word_count": 800,
                    "extraction_method": "webpage",
                    "extracted_at": "2026-09-18T13:58:44.672Z"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = Field(default=False, description="Whether operation was successful")
    error: dict = Field(..., description="Error details")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "INVALID_FILE_TYPE",
                    "message": "File type not allowed. Allowed: pdf, txt, docx, doc, jpg, jpeg, png"
                }
            }
        }
