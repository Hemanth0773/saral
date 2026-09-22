"""
Text-to-Speech service using Microsoft Edge TTS.
Converts text to speech audio for English and Kannada languages.
"""

import os
import uuid
import time
import asyncio
from typing import Dict, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    import edge_tts
except ImportError:
    edge_tts = None


class TTSServiceError(Exception):
    """Base exception for TTS service errors"""
    pass


class TTSServiceUnavailableError(TTSServiceError):
    """Exception raised when TTS engine is unavailable"""
    pass


class TTSVoiceError(TTSServiceError):
    """Exception raised when voice/model is not available"""
    pass


class TTSService:
    """
    Text-to-Speech service using Microsoft Edge TTS engine.

    Uses the edge-tts library which provides free access to Microsoft's
    neural TTS voices without requiring an API key.

    Supports English (en) and Kannada (kn) out of the box, with
    extensible language/voice mapping.
    """

    _instance: Optional['TTSService'] = None
    _initialized: bool = False

    MAX_TEXT_LENGTH: int = settings.MAX_DOCUMENT_LENGTH

    LANGUAGE_VOICE_MAP: Dict[str, str] = {
        "en": "en-US-AriaNeural",
        "kn": "kn-IN-GaganNeural",
    }

    def __new__(cls) -> 'TTSService':
        """Singleton pattern to ensure TTS engine is initialized only once."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize TTS service."""
        if not self._initialized:
            self._initialized = True
            self._output_dir = os.path.join(settings.GENERATED_DIRECTORY, "audio")
            os.makedirs(self._output_dir, exist_ok=True)
            logger.info(f"TTS service initialized. Output directory: {self._output_dir}")

    def _validate_language(self, language: str) -> str:
        """
        Validate and normalize language code.

        Args:
            language: ISO 639-1 language code (e.g., 'en', 'kn')

        Returns:
            Normalized lowercase language code

        Raises:
            TTSServiceError: If language is not supported
        """
        lang = language.lower().strip()
        if lang not in self.LANGUAGE_VOICE_MAP:
            raise TTSServiceError(
                f"Unsupported language: {language}. Supported languages: {list(self.LANGUAGE_VOICE_MAP.keys())}"
            )
        return lang

    def _validate_text(self, text: str) -> str:
        """
        Validate text input.

        Args:
            text: Text to validate

        Returns:
            Stripped text

        Raises:
            TTSServiceError: If text is empty or too long
        """
        if not text or not text.strip():
            raise TTSServiceError("Text must not be empty")

        stripped = text.strip()
        if len(stripped) > self.MAX_TEXT_LENGTH:
            raise TTSServiceError(
                f"Text exceeds maximum length of {self.MAX_TEXT_LENGTH} characters"
            )
        return stripped

    def _get_safe_filename(self, language: str) -> str:
        """
        Generate a safe, unique filename for audio output.

        Args:
            language: Language code for the voice used

        Returns:
            Safe filename with .mp3 extension
        """
        safe_id = uuid.uuid4().hex[:12]
        return f"tts_{language}_{safe_id}.mp3"

    def _get_file_path(self, filename: str) -> str:
        """
        Get the full file path for an audio file, ensuring it's within the output directory.

        Args:
            filename: Safe filename (no path components)

        Returns:
            Full path within the output directory

        Raises:
            TTSServiceError: If path traversal is detected
        """
        # Prevent path traversal - only allow alphanumeric, underscore, hyphen, dot
        if not all(c.isalnum() or c in '_-.' for c in filename):
            raise TTSServiceError("Invalid filename")

        full_path = os.path.normpath(os.path.join(self._output_dir, filename))

        # Ensure the path is within the output directory
        if not full_path.startswith(os.path.normpath(self._output_dir)):
            raise TTSServiceError("Path traversal detected")

        return full_path

    async def generate_speech(
        self,
        text: str,
        language: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None
    ) -> Tuple[str, Dict]:
        """
        Generate speech audio from text using edge-tts.

        This is an async method that must be awaited. It should be called
        from within an async context (e.g., a FastAPI async route).

        Args:
            text: Text to convert to speech
            language: ISO 639-1 language code (e.g., 'en', 'kn')
            voice: Optional specific voice identifier (overrides language default)
            speed: Optional speech rate (e.g., 1.2 for 20% faster)

        Returns:
            Tuple of (audio_file_path, metadata_dict)

        Raises:
            TTSServiceError: If text or language is invalid
            TTSServiceUnavailableError: If TTS engine fails
            TTSVoiceError: If specified voice is not available
        """
        # Validate inputs
        validated_text = self._validate_text(text)
        validated_lang = self._validate_language(language)

        # Determine voice
        selected_voice = voice or self.LANGUAGE_VOICE_MAP[validated_lang]

        # Validate voice if explicitly provided
        if voice and voice not in self.LANGUAGE_VOICE_MAP.values():
            logger.warning(f"Using non-standard voice: {voice}")

        # Generate filename and path
        filename = self._get_safe_filename(validated_lang)
        file_path = self._get_file_path(filename)

        start_time = time.time()

        try:
            communicate = edge_tts.Communicate(
                validated_text,
                selected_voice,
                rate=f"{speed:+.0f}%" if speed and speed != 1.0 else "+0%",
            )
            await communicate.save(file_path)

            generation_time = int((time.time() - start_time) * 1000)

            if not os.path.exists(file_path):
                raise TTSServiceUnavailableError("Audio file was not generated")

            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise TTSServiceUnavailableError("Generated audio file is empty")

            logger.info(
                f"TTS generated: language={validated_lang}, "
                f"text_length={len(validated_text)}, "
                f"file_size={file_size}, "
                f"time={generation_time}ms"
            )

            metadata = {
                "language": validated_lang,
                "voice": selected_voice,
                "text_length": len(validated_text),
                "file_size_bytes": file_size,
                "duration_ms": generation_time,
                "filename": filename,
                "content_type": "audio/mpeg",
            }

            return file_path, metadata

        except TTSServiceError:
            raise
        except asyncio.TimeoutError:
            logger.error(f"TTS operation timed out for language: {validated_lang}")
            raise TTSServiceUnavailableError("TTS service timed out")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"TTS generation failed: {error_msg}")

            if "voice" in error_msg.lower() or "language" in error_msg.lower():
                raise TTSVoiceError(f"Voice not available: {error_msg}")
            else:
                raise TTSServiceUnavailableError(f"TTS engine unavailable: {error_msg}")

    def cleanup_audio_file(self, file_path: str) -> None:
        """
        Safely delete a temporary audio file.

        Args:
            file_path: Path to the audio file to delete
        """
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up audio file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up audio file {file_path}: {e}")


# Global TTS service instance
tts_service = TTSService()


async def synthesize_speech(
    text: str,
    language: str,
    voice: Optional[str] = None,
    speed: Optional[float] = None
) -> Tuple[str, Dict]:
    """
    Async convenience function to synthesize speech using the global TTS service.

    Args:
        text: Text to convert to speech
        language: ISO 639-1 language code (e.g., 'en', 'kn')
        voice: Optional specific voice identifier
        speed: Optional speech rate

    Returns:
        Tuple of (audio_file_path, metadata_dict)
    """
    return await tts_service.generate_speech(text, language, voice, speed)
