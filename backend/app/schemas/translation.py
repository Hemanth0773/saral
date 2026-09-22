"""
Pydantic schemas for translation request and response.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List


class TranslationRequest(BaseModel):
    """Request model for translation endpoint."""
    text: str = Field(..., min_length=1, description="Text to translate")
    source_language: str = Field(..., description="Source language code (e.g., 'en', 'kn')")
    target_language: str = Field(..., description="Target language code (e.g., 'en', 'kn')")

    @validator('text')
    def text_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Text must not be empty')
        return v.strip()

    @validator('source_language', 'target_language')
    def language_code_must_be_valid(cls, v):
        allowed_languages = ['en', 'kn']  # English and Kannada
        if v not in allowed_languages:
            raise ValueError(f'Language code must be one of {allowed_languages}')
        return v.lower()


class TranslationResponse(BaseModel):
    """Response model for translation endpoint."""
    success: bool = Field(default=True, description="Whether translation was successful")
    translated_text: str = Field(..., description="Translated text")
    source_language: str = Field(..., description="Source language code")
    target_language: str = Field(..., description="Target language code")
    model_used: str = Field(..., description="Translation model used")
    character_count: int = Field(..., description="Number of characters in original text")
    translated_character_count: int = Field(..., description="Number of characters in translated text")


class BatchTranslationRequest(BaseModel):
    """Request model for batch translation endpoint."""
    texts: List[str] = Field(..., min_length=1, description="List of texts to translate")
    source_language: str = Field(..., description="Source language code (e.g., 'en', 'kn')")
    target_language: str = Field(..., description="Target language code (e.g., 'en', 'kn')")

    @validator('texts')
    def texts_must_not_be_empty(cls, v):
        for i, text in enumerate(v):
            if not text or not text.strip():
                raise ValueError(f'Text at index {i} must not be empty')
        return [text.strip() for text in v]

    @validator('source_language', 'target_language')
    def language_code_must_be_valid(cls, v):
        allowed_languages = ['en', 'kn']  # English and Kannada
        if v not in allowed_languages:
            raise ValueError(f'Language code must be one of {allowed_languages}')
        return v.lower()


class BatchTranslationResponse(BaseModel):
    """Response model for batch translation endpoint."""
    success: bool = Field(default=True, description="Whether batch translation was successful")
    translations: List[TranslationResponse] = Field(..., description="List of translation results")
    batch_size: int = Field(..., description="Number of texts translated")