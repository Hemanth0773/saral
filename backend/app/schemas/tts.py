"""
Pydantic schemas for text-to-speech request and response.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List


class TTSRequest(BaseModel):
    """Request model for text-to-speech endpoint."""
    text: str = Field(..., min_length=1, description="Text to convert to speech")
    language: str = Field(..., description="Language code (e.g., 'en', 'kn')")
    voice: Optional[str] = Field(None, description="Optional specific voice identifier")
    speed: Optional[float] = Field(default=1.0, ge=0.5, le=2.0, description="Speech rate multiplier (0.5 to 2.0)")

    @validator('text')
    def text_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Text must not be empty')
        return v.strip()

    @validator('language')
    def language_code_must_be_valid(cls, v):
        allowed_languages = ['en', 'kn']
        if v.lower() not in allowed_languages:
            raise ValueError(f'Language code must be one of {allowed_languages}')
        return v.lower()


class TTSResponse(BaseModel):
    """Response model for text-to-speech endpoint."""
    success: bool = Field(default=True, description="Whether TTS generation was successful")
    audio_url: str = Field(..., description="URL path to the generated audio file")
    filename: str = Field(..., description="Generated audio filename")
    language: str = Field(..., description="Language code used for synthesis")
    voice: str = Field(..., description="Voice identifier used")
    text_length: int = Field(..., description="Number of characters in the input text")
    file_size_bytes: int = Field(..., description="Size of the generated audio file in bytes")
    content_type: str = Field(..., description="MIME type of the audio file")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
