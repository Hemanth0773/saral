"""
Text-to-Speech API routes.
Handles speech synthesis endpoints for English and Kannada languages.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.tts import TTSRequest, TTSResponse
from app.schemas.document import ErrorResponse
from app.services.tts_service import (
    synthesize_speech,
    TTSServiceError,
    TTSServiceUnavailableError,
    TTSVoiceError
)

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/tts",
    response_model=TTSResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        503: {"model": ErrorResponse, "description": "TTS service unavailable"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["translation"],
    summary="Generate speech from text (TTS)",
    description="""Convert text to speech audio using Microsoft Edge TTS neural voices.

    Supported languages:
    - English (en): US English voice
    - Kannada (kn): Indian Kannada neural voice

    The generated audio is MP3 format and suitable for browser playback.

    Audio files are stored temporarily and can be served via a dedicated media endpoint.
    """,
)
async def tts_endpoint(request: TTSRequest) -> dict:
    """
    Convert text to speech audio.

    Args:
        request: TTSRequest with text, language, optional voice and speed

    Returns:
        TTSResponse with audio file reference and metadata

    Raises:
        HTTPException: If TTS generation fails
    """
    try:
        text_length = len(request.text)
        logger.info(
            f"TTS request: language={request.language}, "
            f"text_length={text_length}"
        )

        # Validate text length (using a reasonable limit)
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

        # Perform TTS
        try:
            file_path, metadata = await synthesize_speech(
                text=request.text,
                language=request.language,
                voice=request.voice,
                speed=request.speed
            )
        except TTSServiceError as e:
            logger.error(f"TTS service error: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail={
                    "success": False,
                    "error": {
                        "code": "TTS_SERVICE_ERROR",
                        "message": "Text-to-speech service unavailable. Please try again later."
                    }
                }
            )
        except TTSServiceUnavailableError as e:
            logger.error(f"TTS engine unavailable: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail={
                    "success": False,
                    "error": {
                        "code": "TTS_ENGINE_UNAVAILABLE",
                        "message": "TTS engine is not available. Please try again later."
                    }
                }
            )
        except TTSVoiceError as e:
            logger.error(f"TTS voice error: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail={
                    "success": False,
                    "error": {
                        "code": "TTS_VOICE_UNAVAILABLE",
                        "message": "Requested voice is not available. Please try a different language or voice."
                    }
                }
            )
        except Exception as e:
            logger.error(f"Unexpected TTS error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": {
                        "code": "TTS_GENERATION_FAILED",
                        "message": "Speech generation failed. Please try again."
                    }
                }
            )

        # Build audio URL (safe, no filesystem path exposure)
        filename = metadata["filename"]
        audio_url = f"/api/media/audio/{filename}"

        response = TTSResponse(
            success=True,
            audio_url=audio_url,
            filename=filename,
            language=metadata["language"],
            voice=metadata["voice"],
            text_length=metadata["text_length"],
            file_size_bytes=metadata["file_size_bytes"],
            content_type=metadata["content_type"],
            processing_time_ms=metadata["duration_ms"]
        )

        logger.info(
            f"TTS completed: language={request.language}, "
            f"file_size={metadata['file_size_bytes']} bytes"
        )

        return response.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in tts_endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "TTS_FAILED",
                    "message": "An unexpected error occurred during speech generation"
                }
            }
        )


@router.get(
    "/media/audio/{filename}",
    responses={
        404: {"model": ErrorResponse, "description": "Audio file not found"},
    },
    tags=["translation"],
    summary="Serve generated audio file",
    description="Retrieve a previously generated TTS audio file by filename.",
)
async def serve_audio(filename: str):
    """
    Serve a generated audio file.

    Args:
        filename: Audio filename returned from the TTS endpoint

    Returns:
        FileResponse with the audio file

    Raises:
        HTTPException: If file is not found or path is invalid
    """
    from app.services.tts_service import TTSService

    service = TTSService()
    file_path = service._get_file_path(filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "AUDIO_NOT_FOUND",
                    "message": "Audio file not found"
                }
            }
        )

    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=filename
    )
