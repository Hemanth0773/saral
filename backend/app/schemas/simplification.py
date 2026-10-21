"""
Pydantic schemas for LLM-based text simplification.
Used for request/response validation of simplification operations.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class PreservedFact(BaseModel):
    """A critical fact that must be preserved in simplification"""
    fact_type: str = Field(..., description="Type of fact: deadline, money, percentage, age, quantity, requirement, contact, other")
    value: str = Field(..., description="The actual value (e.g., '31 December 2026', '₹2,50,000')")
    source_text: str = Field(..., description="The sentence/phrase where the fact appears in source")
    preserved_in_simplified: bool = Field(default=False, description="Whether fact was preserved in simplified text")


class SimplificationSection(BaseModel):
    """A section of simplified text with metadata"""
    title: Optional[str] = Field(None, description="Section title if present")
    original_text: str = Field(..., description="Original section text")
    simplified_text: str = Field(..., description="Simplified section text")
    grade_level_improvement: Optional[int] = Field(None, description="Estimated grade level reduction")


class SimplificationRequest(BaseModel):
    """Request to simplify text"""
    text: str = Field(..., min_length=1, max_length=50000, description="Text to simplify (max 50,000 chars)")
    target_grade_level: int = Field(default=5, ge=1, le=12, description="Target reading grade level (1-12)")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "The applicant shall submit the duly completed application form along with the requisite supporting documentation prior to the prescribed deadline.",
                "target_grade_level": 5
            }
        }


class ReadabilityMetrics(BaseModel):
    """Readability metrics of one text"""
    word_count: int = Field(default=0, description="Number of words")
    sentence_count: int = Field(default=0, description="Number of sentences")
    average_sentence_length: float = Field(default=0.0, description="Words per sentence")
    flesch_reading_ease: Optional[float] = Field(None, description="Flesch reading ease (0-100)")
    flesch_kincaid_grade: Optional[float] = Field(None, description="Flesch-Kincaid grade level")


class ReadabilitySummary(BaseModel):
    """The measured readability of a simplified document"""
    original: ReadabilityMetrics = Field(default_factory=ReadabilityMetrics)
    simplified: ReadabilityMetrics = Field(default_factory=ReadabilityMetrics)
    target_grade_level: int = Field(default=5, description="The grade level that was asked for")
    target_achieved: bool = Field(default=False, description="Whether the target grade level was reached")


class SummaryItem(BaseModel):
    """One fact of the canonical Instant Summary"""
    id: str = Field(..., description="Stable identifier for the item")
    kind: str = Field(
        ...,
        description=(
            "Category of the fact: deadline, date, document, money, percentage, "
            "age, condition, eligibility, contact or procedure"
        ),
    )
    label: str = Field(..., description="Label shown before the fact, for example 'Documents needed'")
    value: str = Field(..., description="The fact itself")
    severity: str = Field(default="info", description="info, warning or critical")


class SimplificationResponse(BaseModel):
    """Response from simplification endpoint"""
    success: bool = Field(default=True, description="Whether simplification was successful")
    document_id: str = Field(..., description="Unique document identifier")
    original_text: str = Field(..., description="Original input text (unchanged)")
    simplified_text: str = Field(..., description="Simplified output text")
    target_grade_level: int = Field(..., description="Target grade level requested")
    model_used: str = Field(..., description="LLM model used for simplification")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    sections: List[SimplificationSection] = Field(default_factory=list, description="Sections if text was chunked")
    preserved_facts: List[PreservedFact] = Field(default_factory=list, description="Critical facts and their preservation status")
    key_terms: List[str] = Field(default_factory=list, description="Important technical/legal terms preserved")
    instant_summary: List[SummaryItem] = Field(
        default_factory=list,
        description=(
            "Canonical Instant Summary. The website and the Chrome extension both "
            "render this list, so they always show the same facts."
        ),
    )
    readability: Optional[ReadabilitySummary] = Field(
        None,
        description=(
            "The measured readability of the simplified text. The website and the "
            "Chrome extension both show this result."
        ),
    )
    validation_passed: bool = Field(default=True, description="Whether fact preservation validation passed")
    validation_failures: List[str] = Field(default_factory=list, description="Any validation issues detected")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional processing metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "doc_20260921_120000_abcdef12",
                "original_text": "Eligible applicants must submit the application before 31 December 2026. The assistance amount is ₹2,50,000. Applicants must be at least 18 years old.",
                "simplified_text": "You must apply before 31 December 2026. The government gives ₹2,50,000. You must be at least 18 years old.",
                "target_grade_level": 5,
                "model_used": "gpt-3.5-turbo",
                "processing_time_ms": 1250,
                "sections": [],
                "preserved_facts": [
                    {
                        "fact_type": "deadline",
                        "value": "31 December 2026",
                        "source_text": "must submit the application before 31 December 2026",
                        "preserved_in_simplified": True
                    },
                    {
                        "fact_type": "money",
                        "value": "₹2,50,000",
                        "source_text": "The assistance amount is ₹2,50,000",
                        "preserved_in_simplified": True
                    },
                    {
                        "fact_type": "age",
                        "value": "18 years",
                        "source_text": "at least 18 years old",
                        "preserved_in_simplified": True
                    }
                ],
                "key_terms": ["eligible", "applicants", "assistance"],
                "validation_passed": True,
                "validation_failures": [],
                "metadata": {
                    "retry_count": 0,
                    "chunks": 1
                }
            }
        }
