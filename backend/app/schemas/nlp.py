"""
Pydantic schemas for NLP processing.
Used for request/response validation of linguistic analysis.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class SentenceToken(BaseModel):
    """Individual sentence with positional information"""
    text: str = Field(..., description="Sentence text")
    start_index: int = Field(..., description="Start character index in original text")
    end_index: int = Field(..., description="End character index in original text")
    sentence_id: int = Field(..., description="Sequential sentence identifier")


class NamedEntity(BaseModel):
    """Named entity recognized in text"""
    text: str = Field(..., description="Entity text")
    label: str = Field(..., description="Entity type (PERSON, ORG, GPE, etc.)")
    start_index: int = Field(..., description="Start character index in original text")
    end_index: int = Field(..., description="End character index in original text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class POSTag(BaseModel):
    """Part-of-speech tag for a token"""
    text: str = Field(..., description="Token text")
    pos: str = Field(..., description="Universal POS tag (NOUN, VERB, ADJ, etc.)")
    tag: str = Field(..., description="Detailed POS tag")
    index: int = Field(..., description="Position of token in sentence")


class KeyPhrase(BaseModel):
    """Extracted key phrase with importance score"""
    text: str = Field(..., description="Key phrase text")
    score: float = Field(..., ge=0.0, le=1.0, description="Importance/relevance score")
    count: int = Field(..., description="Number of occurrences in text")


class NLPProcessingMetadata(BaseModel):
    """Metadata about the NLP processing"""
    model_used: str = Field(..., description="spaCy model used for processing")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    language_detected: str = Field(..., description="Detected language code")
    timestamp: str = Field(..., description="ISO 8601 timestamp of processing")


class NLPProcessingResponse(BaseModel):
    """Response from NLP preprocessing endpoint"""
    success: bool = Field(default=True, description="Whether processing was successful")
    document_id: str = Field(..., description="Unique document identifier")
    normalized_text: str = Field(..., description="Cleaned and normalized input text")
    sentences: List[SentenceToken] = Field(default_factory=list, description="Extracted sentences")
    entities: List[NamedEntity] = Field(default_factory=list, description="Named entities found")
    pos_tags: List[POSTag] = Field(default_factory=list, description="Part-of-speech tags")
    key_phrases: List[KeyPhrase] = Field(default_factory=list, description="Extracted key phrases")
    processing_metadata: NLPProcessingMetadata = Field(..., description="Processing metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "doc_20260921_120000_abcdef12",
                "normalized_text": "The Government of India launched a new housing assistance scheme for economically weaker sections. The scheme aims to provide affordable housing solutions.",
                "sentences": [
                    {
                        "text": "The Government of India launched a new housing assistance scheme for economically weaker sections.",
                        "start_index": 0,
                        "end_index": 102,
                        "sentence_id": 0
                    },
                    {
                        "text": "The scheme aims to provide affordable housing solutions.",
                        "start_index": 103,
                        "end_index": 140,
                        "sentence_id": 1
                    }
                ],
                "entities": [
                    {
                        "text": "Government of India",
                        "label": "ORG",
                        "start_index": 4,
                        "end_index": 23,
                        "confidence": 0.98
                    },
                    {
                        "text": "economically weaker sections",
                        "label": "NORP",
                        "start_index": 65,
                        "end_index": 89,
                        "confidence": 0.87
                    }
                ],
                "pos_tags": [
                    {
                        "text": "Government",
                        "pos": "NOUN",
                        "tag": "NNP",
                        "index": 1
                    },
                    {
                        "text": "launched",
                        "pos": "VERB",
                        "tag": "VBD",
                        "index": 2
                    }
                ],
                "key_phrases": [
                    {
                        "text": "housing assistance scheme",
                        "score": 0.95,
                        "count": 2
                    },
                    {
                        "text": "affordable housing solutions",
                        "score": 0.88,
                        "count": 1
                    }
                ],
                "processing_metadata": {
                    "model_used": "en_core_web_sm",
                    "processing_time_ms": 125,
                    "language_detected": "en",
                    "timestamp": "2026-09-21T12:00:00.672Z"
                }
            }
        }