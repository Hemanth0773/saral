"""
Pydantic schemas for structured information extraction.
Used for request/response validation of information extraction operations.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ExtractedDeadline(BaseModel):
    """Extracted deadline information"""
    date: str = Field(..., description="ISO 8601 date format (YYYY-MM-DD)")
    description: Optional[str] = Field(None, description="Deadline description (e.g., 'Application deadline')")
    original_text: str = Field(..., description="Original text where date was found")


class ExtractedDate(BaseModel):
    """Extracted important date"""
    date: str = Field(..., description="ISO 8601 date format (YYYY-MM-DD)")
    description: Optional[str] = Field(None, description="Date description")
    original_text: str = Field(..., description="Original text where date was found")


class ExtractedRequirement(BaseModel):
    """Extracted eligibility requirement"""
    requirement: str = Field(..., description="Requirement text")
    category: Optional[str] = Field(None, description="Category (e.g., 'education', 'employment', 'income')")
    original_text: str = Field(..., description="Original text")


class ExtractedAgeRequirement(BaseModel):
    """Extracted age requirement"""
    minimum_age: Optional[int] = Field(None, description="Minimum age in years")
    maximum_age: Optional[int] = Field(None, description="Maximum age in years")
    original_text: str = Field(..., description="Original text")


class ExtractedDocument(BaseModel):
    """Required document for application"""
    name: str = Field(..., description="Document name (e.g., 'Aadhaar card')")
    description: Optional[str] = Field(None, description="Additional description or notes")
    original_text: str = Field(..., description="Original text")


class ExtractedMonetaryAmount(BaseModel):
    """Extracted monetary amount"""
    amount: str = Field(..., description="Amount with currency (e.g., '₹2,50,000')")
    amount_normalized: Optional[str] = Field(None, description="Normalized amount (e.g., '250000')")
    currency: Optional[str] = Field(None, description="Currency symbol or code")
    purpose: Optional[str] = Field(None, description="Purpose of amount (e.g., 'assistance', 'fee', 'interest')")
    original_text: str = Field(..., description="Original text")


class ExtractedPercentage(BaseModel):
    """Extracted percentage value"""
    percentage: str = Field(..., description="Percentage value (e.g., '5%')")
    value: float = Field(..., description="Numeric percentage value")
    purpose: Optional[str] = Field(None, description="Purpose (e.g., 'interest rate', 'discount')")
    original_text: str = Field(..., description="Original text")


class ExtractedProcedure(BaseModel):
    """Application procedure step"""
    step_number: Optional[int] = Field(None, description="Step order")
    description: str = Field(..., description="Procedure description")
    original_text: str = Field(..., description="Original text")


class ExtractedCondition(BaseModel):
    """Important condition or exception"""
    condition: str = Field(..., description="Condition text")
    type: Optional[str] = Field(None, description="Type (e.g., 'exception', 'requirement', 'warning')")
    original_text: str = Field(..., description="Original text")


class ExtractedContactInfo(BaseModel):
    """Contact information"""
    type: str = Field(..., description="Contact type (e.g., 'phone', 'email', 'address', 'office')")
    value: str = Field(..., description="Contact value")
    original_text: str = Field(..., description="Original text")


class ExtractedLocation(BaseModel):
    """Geographic location or office information"""
    location: str = Field(..., description="Location name or address")
    type: Optional[str] = Field(None, description="Type (e.g., 'office', 'regional', 'headquarters')")
    original_text: str = Field(..., description="Original text")


class ExtractedOrganization(BaseModel):
    """Organization or entity mentioned"""
    name: str = Field(..., description="Organization name")
    role: Optional[str] = Field(None, description="Role or context (e.g., 'implementing agency')")
    original_text: str = Field(..., description="Original text")


class StructuredInformation(BaseModel):
    """Complete structured information extracted from document"""
    title: Optional[str] = Field(None, description="Document/scheme title")
    summary: Optional[str] = Field(None, description="Summary of the document or scheme")

    deadlines: List[ExtractedDeadline] = Field(default_factory=list, description="Application deadlines")
    important_dates: List[ExtractedDate] = Field(default_factory=list, description="Other important dates")

    eligibility_requirements: List[ExtractedRequirement] = Field(
        default_factory=list,
        description="Eligibility criteria"
    )
    age_requirements: List[ExtractedAgeRequirement] = Field(
        default_factory=list,
        description="Age-related requirements"
    )

    required_documents: List[ExtractedDocument] = Field(
        default_factory=list,
        description="Documents required for application"
    )

    financial_information: List[ExtractedMonetaryAmount] = Field(
        default_factory=list,
        description="Monetary amounts (assistance, fees, interest rates, etc.)"
    )
    percentages: List[ExtractedPercentage] = Field(
        default_factory=list,
        description="Percentage values"
    )

    application_procedure: List[ExtractedProcedure] = Field(
        default_factory=list,
        description="Steps for application"
    )

    important_conditions: List[ExtractedCondition] = Field(
        default_factory=list,
        description="Important conditions, exceptions, or warnings"
    )

    contact_information: List[ExtractedContactInfo] = Field(
        default_factory=list,
        description="Contact information"
    )

    locations: List[ExtractedLocation] = Field(
        default_factory=list,
        description="Geographic locations or offices"
    )

    organizations: List[ExtractedOrganization] = Field(
        default_factory=list,
        description="Organizations and entities mentioned"
    )


class ExtractionRequest(BaseModel):
    """Request to extract structured information"""
    text: str = Field(..., min_length=1, max_length=100000, description="Text to extract from (max 100,000 chars)")
    extract_title: bool = Field(default=True, description="Whether to extract document title")
    extract_summary: bool = Field(default=True, description="Whether to generate summary")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Eligible applicants must submit the application before 31 December 2026. The assistance amount is ₹2,50,000. Applicants must be at least 18 years old and must submit Aadhaar, income certificate, and bank account details.",
                "extract_title": True,
                "extract_summary": True
            }
        }


class ExtractionResponse(BaseModel):
    """Response from structured information extraction"""
    success: bool = Field(default=True, description="Whether extraction was successful")
    document_id: str = Field(..., description="Unique document identifier")
    original_text: str = Field(..., description="Original input text (unchanged)")
    structured_information: StructuredInformation = Field(..., description="Extracted structured information")
    extraction_method: str = Field(..., description="Method used for extraction (e.g., 'deterministic', 'llm', 'hybrid')")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional processing metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "doc_20260921_130000_abc123",
                "original_text": "Eligible applicants must submit the application before 31 December 2026. The assistance amount is ₹2,50,000. Applicants must be at least 18 years old and must submit Aadhaar, income certificate, and bank account details.",
                "structured_information": {
                    "title": None,
                    "summary": None,
                    "deadlines": [
                        {
                            "date": "2026-12-31",
                            "description": "Application submission deadline",
                            "original_text": "must submit the application before 31 December 2026"
                        }
                    ],
                    "important_dates": [],
                    "eligibility_requirements": [],
                    "age_requirements": [
                        {
                            "minimum_age": 18,
                            "maximum_age": None,
                            "original_text": "at least 18 years old"
                        }
                    ],
                    "required_documents": [
                        {
                            "name": "Aadhaar",
                            "description": None,
                            "original_text": "Aadhaar"
                        },
                        {
                            "name": "Income certificate",
                            "description": None,
                            "original_text": "income certificate"
                        },
                        {
                            "name": "Bank account details",
                            "description": None,
                            "original_text": "bank account details"
                        }
                    ],
                    "financial_information": [
                        {
                            "amount": "₹2,50,000",
                            "amount_normalized": "250000",
                            "currency": "₹",
                            "purpose": "assistance",
                            "original_text": "The assistance amount is ₹2,50,000"
                        }
                    ],
                    "percentages": [],
                    "application_procedure": [],
                    "important_conditions": [],
                    "contact_information": [],
                    "locations": [],
                    "organizations": []
                },
                "extraction_method": "deterministic",
                "processing_time_ms": 45,
                "metadata": {
                    "facts_preserved": True,
                    "facts_count": 3
                }
            }
        }
