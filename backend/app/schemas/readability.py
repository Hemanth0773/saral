"""
Pydantic schemas for readability analysis.
Used for request/response validation of readability analysis operations.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ReadabilityMetrics(BaseModel):
    """Readability metrics for a single text sample"""
    word_count: int = Field(..., description="Number of words in text")
    sentence_count: int = Field(..., description="Number of sentences in text")
    character_count: int = Field(..., description="Number of characters in text")
    syllable_count: int = Field(..., description="Total syllables in text")
    average_sentence_length: float = Field(..., description="Average words per sentence", examples=[8.5])
    flesch_reading_ease: Optional[float] = Field(None, description="Flesch Reading Ease score (0-100, higher=easier)", examples=[72.1])
    flesch_kincaid_grade: Optional[float] = Field(None, description="Flesch-Kincaid Grade Level (US grade)", examples=[5.4])


class ReadabilityComparison(BaseModel):
    """Comparison metrics between original and simplified text"""
    grade_level_improvement: float = Field(..., description="Reduction in grade level (positive=improvement)", examples=[5.2])
    reading_ease_improvement: float = Field(..., description="Increase in reading ease (positive=improvement)", examples=[29.6])
    sentence_length_reduction: float = Field(..., description="Reduction in average sentence length", examples=[6.25])
    target_grade_level: int = Field(..., description="Target grade level specified (1-12)", examples=[5])
    simplified_grade_level: Optional[float] = Field(None, description="Calculated grade level of simplified text", examples=[5.4])
    target_achieved: bool = Field(..., description="Whether simplified text meets target grade level", examples=[False])


class ReadabilityAnalysisRequest(BaseModel):
    """Request to analyze readability of texts"""
    original_text: str = Field(..., min_length=1, max_length=50000, description="Original text to analyze")
    simplified_text: str = Field(..., min_length=1, max_length=50000, description="Simplified text to analyze")
    target_grade_level: Optional[int] = Field(default=5, ge=1, le=12, description="Target reading grade level (1-12), default 5")

    class Config:
        json_schema_extra = {
            "example": {
                "original_text": "Applicants who satisfy the eligibility requirements must submit the application prior to the prescribed deadline.",
                "simplified_text": "You must meet the rules and send your application before the deadline.",
                "target_grade_level": 5
            }
        }


class ReadabilityAnalysisResponse(BaseModel):
    """Response from readability analysis endpoint"""
    success: bool = Field(default=True, description="Whether analysis was successful")
    supported: bool = Field(default=True, description="Whether readability metrics are supported for this language")
    message: Optional[str] = Field(None, description="Status message if not supported")

    original: Optional[ReadabilityMetrics] = Field(None, description="Metrics for original text")
    simplified: Optional[ReadabilityMetrics] = Field(None, description="Metrics for simplified text")
    comparison: Optional[ReadabilityComparison] = Field(None, description="Comparison between original and simplified")

    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    language: str = Field(..., description="Detected language code (en, kn, hi, ta, te, ml, other)")
    timestamp: str = Field(..., description="ISO 8601 timestamp of analysis")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "supported": True,
                "original": {
                    "word_count": 13,
                    "sentence_count": 1,
                    "character_count": 103,
                    "syllable_count": 21,
                    "average_sentence_length": 13.0,
                    "flesch_reading_ease": 42.5,
                    "flesch_kincaid_grade": 10.8
                },
                "simplified": {
                    "word_count": 12,
                    "sentence_count": 2,
                    "character_count": 76,
                    "syllable_count": 14,
                    "average_sentence_length": 6.0,
                    "flesch_reading_ease": 72.1,
                    "flesch_kincaid_grade": 5.6
                },
                "comparison": {
                    "grade_level_improvement": 5.2,
                    "reading_ease_improvement": 29.6,
                    "sentence_length_reduction": 7.0,
                    "target_grade_level": 5,
                    "simplified_grade_level": 5.6,
                    "target_achieved": False
                },
                "processing_time_ms": 45,
                "language": "en",
                "timestamp": "2026-09-21T16:18:47.204Z"
            }
        }
