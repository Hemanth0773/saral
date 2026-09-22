"""
Pydantic schemas for M7 advanced fact validation.
Used for request/response validation of cross-document fact validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class ValidationStatus(str, Enum):
    """Validation result status"""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    INCONCLUSIVE = "INCONCLUSIVE"


class FactType(str, Enum):
    """Types of facts being validated"""
    DATE = "date"
    DEADLINE = "deadline"
    DATE_RANGE = "date_range"
    MONETARY_AMOUNT = "monetary_amount"
    PERCENTAGE = "percentage"
    AGE = "age"
    QUANTITY = "quantity"
    REQUIRED_DOCUMENT = "required_document"
    ELIGIBILITY_REQUIREMENT = "eligibility_requirement"
    IMPORTANT_CONDITION = "important_condition"
    CONTACT_INFORMATION = "contact_information"
    LOCATION = "location"
    OTHER = "other"


class FactContradiction(BaseModel):
    """A detected contradiction between documents"""
    fact_type: FactType = Field(..., description="Type of fact that contradicts")
    original_value: str = Field(..., description="Value in original document")
    simplified_value: Optional[str] = Field(None, description="Value in simplified text (if found)")
    structured_value: Optional[str] = Field(None, description="Value in structured information (if found)")
    reason: str = Field(..., description="Explanation of the contradiction")
    severity: str = Field(default="error", description="error | warning")
    original_location: Optional[str] = Field(None, description="Where fact was found in original")
    simplified_location: Optional[str] = Field(None, description="Where fact was found in simplified")


class FactPreservationDetail(BaseModel):
    """Details about a specific fact and whether it was preserved"""
    fact_type: FactType = Field(..., description="Type of fact")
    original_value: str = Field(..., description="Value in original document")
    preserved: bool = Field(..., description="Whether fact was preserved")
    simplified_value: Optional[str] = Field(None, description="Value in simplified text")
    structured_value: Optional[str] = Field(None, description="Value in structured information")
    notes: Optional[str] = Field(None, description="Additional notes about this fact")


class CrossDocumentValidationResult(BaseModel):
    """Result of validating facts across original, simplified, and structured documents"""
    validation_passed: bool = Field(..., description="Whether validation passed")
    overall_status: ValidationStatus = Field(..., description="Overall validation status")

    # Counts
    facts_checked: int = Field(default=0, description="Total number of facts checked")
    facts_preserved: int = Field(default=0, description="Number of facts correctly preserved")
    facts_changed: int = Field(default=0, description="Number of facts that changed")
    facts_missing: int = Field(default=0, description="Number of facts missing from simplified/structured")

    # Details
    contradictions: List[FactContradiction] = Field(default_factory=list, description="List of contradictions found")
    preservation_details: List[FactPreservationDetail] = Field(default_factory=list, description="Details for each checked fact")

    # Metadata
    processing_time_ms: int = Field(default=0, description="Validation processing time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "validation_passed": True,
                "overall_status": "PASS",
                "facts_checked": 8,
                "facts_preserved": 8,
                "facts_changed": 0,
                "facts_missing": 0,
                "contradictions": [],
                "preservation_details": [
                    {
                        "fact_type": "deadline",
                        "original_value": "31 December 2026",
                        "preserved": True,
                        "simplified_value": "December 31, 2026",
                        "structured_value": "2026-12-31",
                        "notes": "Date format normalized and preserved"
                    }
                ],
                "processing_time_ms": 45,
                "metadata": {
                    "validation_method": "deterministic",
                    "simplification_source": "gemini",
                    "extraction_source": "deterministic"
                }
            }
        }


class CrossDocumentValidationRequest(BaseModel):
    """Request to validate facts across documents"""
    original_text: str = Field(..., min_length=1, max_length=100000, description="Original document text (source of truth)")
    simplified_text: Optional[str] = Field(None, max_length=100000, description="Simplified text from M5 (optional)")
    structured_information: Optional[Dict[str, Any]] = Field(None, description="Structured information from M6 (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "original_text": "Eligible applicants must submit before 31 December 2026. The assistance is ₹2,50,000. Must be 18+ years old.",
                "simplified_text": "Send your application by December 31, 2026. You get ₹2,50,000. You must be 18+ years old.",
                "structured_information": {
                    "deadlines": [{"date": "2026-12-31"}],
                    "financial_information": [{"amount": "₹2,50,000"}],
                    "age_requirements": [{"minimum_age": 18}]
                }
            }
        }
