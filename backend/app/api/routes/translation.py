"""
Translation API routes.
Handles translation endpoints for English-Kannada language translation.
"""

from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.translation import (
    TranslationRequest,
    TranslationResponse,
    BatchTranslationRequest,
    BatchTranslationResponse
)
from app.services.translation_service import (
    translate_text,
    batch_translate_texts,
    TranslationServiceError
)

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/translate",
    response_model=TranslationResponse,
    responses={
        400: {"description": "Invalid input"},
        422: {"description": "Validation error"},
        503: {"description": "Translation service unavailable"},
        500: {"description": "Server error"},
    },
    tags=["translation"],
    summary="Translate text between languages",
    description="""Translate text between supported languages (English-Kannada) using Facebook's NLLB model.

    Supported language pairs:
    - English (en) ↔ Kannada (kn)
    - Same-language translation (en→en, kn→kn) returns original text

    The translation preserves all factual information including numbers, dates, and proper nouns.
    """,
)
async def translate_text_endpoint(request: TranslationRequest) -> dict:
    """
    Translate text from source language to target language.

    Args:
        request: TranslationRequest with text, source_language, and target_language

    Returns:
        TranslationResponse with translated text and metadata

    Raises:
        HTTPException: If translation fails or validation fails
    """
    try:
        # Log request details
        text_length = len(request.text)
        logger.info(
            f"Translation request: {request.source_language}→{request.target_language}, "
            f"text_length={text_length}"
        )

        # Validate text length (using same limit as document processing)
        if text_length > settings.MAX_DOCUMENT_LENGTH:
            logger.warning(f"Text too long: {text_length} > {settings.MAX_DOCUMENT_LENGTH}")
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "TEXT_TOO_LONG",
                        "message": f"Text exceeds maximum length of {settings.MAX_DOCUMENT_LENGTH} characters"
                    }
                }
            )

        # Perform translation
        try:
            translated_text, metadata = translate_text(
                text=request.text,
                source_language=request.source_language,
                target_language=request.target_language
            )
        except TranslationServiceError as e:
            logger.error(f"Translation service error: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail={
                    "success": False,
                    "error": {
                        "code": "TRANSLATION_SERVICE_ERROR",
                        "message": "Translation service unavailable. Please try again later."
                    }
                }
            )
        except Exception as e:
            logger.error(f"Unexpected translation error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": {
                        "code": "TRANSLATION_FAILED",
                        "message": "Text translation failed. Please try again."
                    }
                }
            )

        # Prepare response
        response = TranslationResponse(
            translated_text=translated_text,
            source_language=metadata["source_language"],
            target_language=metadata["target_language"],
            model_used=metadata["model_used"],
            character_count=metadata["character_count"],
            translated_character_count=metadata["translated_character_count"]
        )

        logger.info(
            f"Translation completed: {request.source_language}→{request.target_language}, "
            f"{metadata['character_count']}→{metadata['translated_character_count']} chars"
        )

        return response.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in translate_text_endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "TRANSLATION_FAILED",
                    "message": "An unexpected error occurred during translation"
                }
            }
        )


@router.post(
    "/translate/batch",
    response_model=BatchTranslationResponse,
    responses={
        400: {"description": "Invalid input"},
        422: {"description": "Validation error"},
        503: {"description": "Translation service unavailable"},
        500: {"description": "Server error"},
    },
    tags=["translation"],
    summary="Batch translate multiple texts",
    description="""Translate multiple texts between supported languages (English-Kannada) using Facebook's NLLB model.

    Supported language pairs:
    - English (en) ↔ Kannada (kn)
    - Same-language translation (en→en, kn→kn) returns original texts

    Maximum 100 texts per batch request.
    """,
)
async def batch_translate_text_endpoint(request: BatchTranslationRequest) -> dict:
    """
    Batch translate multiple texts from source language to target language.

    Args:
        request: BatchTranslationRequest with texts, source_language, and target_language

    Returns:
        BatchTranslationResponse with list of translation results

    Raises:
        HTTPException: If batch translation fails or validation fails
    """
    try:
        # Log request details
        batch_size = len(request.texts)
        total_chars = sum(len(text) for text in request.texts)
        logger.info(
            f"Batch translation request: {request.source_language}→{request.target_language}, "
            f"batch_size={batch_size}, total_chars={total_chars}"
        )

        # Validate batch size
        if batch_size > 100:
            logger.warning(f"Batch size too large: {batch_size} > 100")
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "BATCH_SIZE_TOO_LARGE",
                        "message": "Batch size exceeds maximum of 100 texts"
                    }
                }
            )

        # Validate individual text lengths
        for i, text in enumerate(request.texts):
            if len(text) > settings.MAX_DOCUMENT_LENGTH:
                logger.warning(f"Text at index {i} too long: {len(text)} > {settings.MAX_DOCUMENT_LENGTH}")
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error": {
                            "code": "TEXT_TOO_LONG",
                            "message": f"Text at index {i} exceeds maximum length of {settings.MAX_DOCUMENT_LENGTH} characters"
                        }
                    }
                )

        # Perform batch translation
        try:
            results = batch_translate_texts(
                texts=request.texts,
                source_language=request.source_language,
                target_language=request.target_language
            )
        except TranslationServiceError as e:
            logger.error(f"Batch translation service error: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail={
                    "success": False,
                    "error": {
                        "code": "TRANSLATION_SERVICE_ERROR",
                        "message": "Translation service unavailable. Please try again later."
                    }
                }
            )
        except Exception as e:
            logger.error(f"Unexpected batch translation error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": {
                        "code": "TRANSLATION_FAILED",
                        "message": "Batch translation failed. Please try again."
                    }
                }
            )

        # Prepare response objects
        translation_responses = []
        for translated_text, metadata in results:
            translation_responses.append(
                TranslationResponse(
                    translated_text=translated_text,
                    source_language=metadata["source_language"],
                    target_language=metadata["target_language"],
                    model_used=metadata["model_used"],
                    character_count=metadata["character_count"],
                    translated_character_count=metadata["translated_character_count"]
                )
            )

        response = BatchTranslationResponse(
            translations=translation_responses,
            batch_size=len(translation_responses)
        )

        logger.info(
            f"Batch translation completed: {request.source_language}→{request.target_language}, "
            f"batch_size={batch_size}"
        )

        # Return full response including success field
        return {
            "success": True,
            "translations": response.translations,
            "batch_size": response.batch_size
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in batch_translate_text_endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "TRANSLATION_FAILED",
                    "message": "An unexpected error occurred during batch translation"
                }
            }
        )