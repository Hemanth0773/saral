"""
Tests for Text-to-Speech (MILESTONE 10).
Tests cover TTS service, API endpoints, and language synthesis functionality.

Note: All real TTS engine calls are mocked. No actual network calls
to Microsoft's TTS service are made during automated tests.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import os
import asyncio

from app.main import app
from app.services.tts_service import (
    TTSService,
    TTSServiceError,
    TTSServiceUnavailableError,
    TTSVoiceError,
    synthesize_speech
)


client = TestClient(app)


class TestTTSService:
    """Test TTS service functionality"""

    def test_tts_service_singleton(self):
        """Test that TTS service follows singleton pattern"""
        service1 = TTSService()
        service2 = TTSService()
        assert service1 is service2

    def test_english_language_mapping(self):
        """Test English language code maps to correct voice"""
        service = TTSService()
        assert service.LANGUAGE_VOICE_MAP['en'] == 'en-US-AriaNeural'

    def test_kannada_language_mapping(self):
        """Test Kannada language code maps to correct voice"""
        service = TTSService()
        assert service.LANGUAGE_VOICE_MAP['kn'] == 'kn-IN-GaganNeural'


class TestTTSServiceValidation:
    """Test TTS service input validation"""

    def test_unsupported_language(self):
        """Test that unsupported language raises error"""
        service = TTSService()
        with pytest.raises(TTSServiceError):
            service._validate_language('fr')

    def test_unsupported_language_case_insensitive(self):
        """Test language validation is case insensitive"""
        service = TTSService()
        result = service._validate_language('EN')
        assert result == 'en'

    def test_empty_text_raises_error(self):
        """Test that empty text raises error"""
        service = TTSService()
        with pytest.raises(TTSServiceError):
            service._validate_text("")

        with pytest.raises(TTSServiceError):
            service._validate_text("   ")

    def test_text_too_long_raises_error(self):
        """Test that text exceeding max length raises error"""
        service = TTSService()
        long_text = "A" * (service.MAX_TEXT_LENGTH + 1)
        with pytest.raises(TTSServiceError):
            service._validate_text(long_text)

    def test_validate_text_strips_whitespace(self):
        """Test that text is stripped"""
        service = TTSService()
        result = service._validate_text("  hello  ")
        assert result == "hello"


class TestTTSServiceFileHandling:
    """Test TTS service file handling"""

    def test_safe_filename_generation(self):
        """Test that filenames are generated safely"""
        service = TTSService()
        filename = service._get_safe_filename('en')
        assert filename.startswith('tts_en_')
        assert filename.endswith('.mp3')
        assert len(filename) > 12

    def test_path_traversal_prevented(self):
        """Test that path traversal is prevented"""
        service = TTSService()
        with pytest.raises(TTSServiceError):
            service._get_file_path("../../../etc/passwd")

    def test_invalid_filename_rejected(self):
        """Test that invalid filenames are rejected"""
        service = TTSService()
        with pytest.raises(TTSServiceError):
            service._get_file_path("file;malicious")

    def test_safe_filename_uniqueness(self):
        """Test that each generated filename is unique"""
        service = TTSService()
        filename1 = service._get_safe_filename('en')
        filename2 = service._get_safe_filename('en')
        assert filename1 != filename2

    def test_cleanup_audio_file(self):
        """Test that audio file cleanup works"""
        service = TTSService()
        test_path = os.path.join(service._output_dir, "test_cleanup.mp3")
        with open(test_path, 'wb') as f:
            f.write(b'fake audio data')

        assert os.path.exists(test_path)
        service.cleanup_audio_file(test_path)
        assert not os.path.exists(test_path)

    def test_cleanup_nonexistent_file(self):
        """Test cleanup doesn't fail on nonexistent file"""
        service = TTSService()
        service.cleanup_audio_file("/nonexistent/path/file.mp3")
        # Should not raise


class TestTTSServiceSpeechGeneration:
    """Test TTS service speech generation (with mocked engine)

    These tests exercise the actual async code path used by FastAPI
    by mocking edge_tts.Communicate but running the real async method.
    """

    @patch('app.services.tts_service.edge_tts')
    def test_successful_speech_generation_en(self, mock_edge_tts):
        """Test successful English speech generation via async path"""
        service = TTSService()

        mock_communicate = MagicMock()
        async def mock_save(path):
            # Create dummy file to pass existence check
            with open(path, 'wb') as f:
                f.write(b'fake audio data')
        mock_communicate.save = mock_save
        mock_edge_tts.Communicate.return_value = mock_communicate

        file_path, metadata = asyncio.run(
            service.generate_speech("Hello", "en")
        )

        assert metadata["language"] == "en"
        assert metadata["voice"] == "en-US-AriaNeural"
        assert metadata["text_length"] == 5
        assert metadata["filename"].endswith('.mp3')
        # Cleanup
        service.cleanup_audio_file(file_path)

    @patch('app.services.tts_service.edge_tts')
    def test_successful_speech_generation_kn(self, mock_edge_tts):
        """Test successful Kannada speech generation via async path"""
        service = TTSService()

        mock_communicate = MagicMock()
        async def mock_save(path):
            with open(path, 'wb') as f:
                f.write(b'fake audio data')
        mock_communicate.save = mock_save
        mock_edge_tts.Communicate.return_value = mock_communicate

        file_path, metadata = asyncio.run(
            service.generate_speech("ನಮಸ್ಕಾರ", "kn")
        )

        assert metadata["language"] == "kn"
        assert "kn-IN" in metadata["voice"]
        assert metadata["text_length"] == len("ನಮಸ್ಕಾರ")
        service.cleanup_audio_file(file_path)

    @patch('app.services.tts_service.edge_tts')
    def test_engine_failure_raises_error(self, mock_edge_tts):
        """Test that engine failure raises TTSServiceUnavailableError"""
        mock_edge_tts.Communicate.side_effect = Exception("Edge TTS unavailable")

        service = TTSService()
        with pytest.raises(TTSServiceUnavailableError):
            asyncio.run(service.generate_speech("Hello", "en"))

    @patch('app.services.tts_service.edge_tts')
    def test_unexpected_error_raises_error(self, mock_edge_tts):
        """Test that unexpected errors are handled"""
        mock_edge_tts.Communicate.side_effect = RuntimeError("Unexpected failure")

        service = TTSService()
        with pytest.raises((TTSServiceUnavailableError, TTSServiceError)):
            asyncio.run(service.generate_speech("Hello", "en"))

    @patch('app.services.tts_service.edge_tts')
    def test_voice_not_available_raises_voice_error(self, mock_edge_tts):
        """Test that voice-related errors raise TTSVoiceError"""
        mock_edge_tts.Communicate.side_effect = Exception("voice not found")

        service = TTSService()
        with pytest.raises(TTSVoiceError):
            asyncio.run(service.generate_speech("Hello", "en"))


class TestTTSAPIEndpoint:
    """Test TTS API endpoint

    These tests use TestClient which runs the async endpoint internally.
    The service layer is mocked to avoid real network calls.
    """

    @patch('app.api.routes.tts.synthesize_speech', new_callable=AsyncMock)
    def test_tts_endpoint_success_en(self, mock_synthesize):
        """Test successful English TTS"""
        mock_synthesize.return_value = (
            '/fake/path/test.mp3',
            {
                "language": "en",
                "voice": "en-US-AriaNeural",
                "text_length": 12,
                "file_size_bytes": 1024,
                "duration_ms": 100,
                "filename": "tts_en_test123.mp3",
                "content_type": "audio/mpeg"
            }
        )

        request_data = {
            "text": "Hello world",
            "language": "en"
        }

        response = client.post("/api/tts", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["audio_url"] == "/api/media/audio/tts_en_test123.mp3"
        assert data["filename"] == "tts_en_test123.mp3"
        assert data["language"] == "en"
        assert data["voice"] == "en-US-AriaNeural"
        assert data["content_type"] == "audio/mpeg"

    @patch('app.api.routes.tts.synthesize_speech', new_callable=AsyncMock)
    def test_tts_endpoint_success_kn(self, mock_synthesize):
        """Test successful Kannada TTS"""
        mock_synthesize.return_value = (
            '/fake/path/test.mp3',
            {
                "language": "kn",
                "voice": "kn-IN-GaganNeural",
                "text_length": 12,
                "file_size_bytes": 2048,
                "duration_ms": 150,
                "filename": "tts_kn_test456.mp3",
                "content_type": "audio/mpeg"
            }
        )

        request_data = {
            "text": "ನಮಸ್ಕಾರ ಜಗತ",
            "language": "kn"
        }

        response = client.post("/api/tts", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["language"] == "kn"
        assert "kn-IN" in data["voice"]

    @patch('app.api.routes.tts.synthesize_speech', new_callable=AsyncMock)
    def test_tts_endpoint_service_error(self, mock_synthesize):
        """Test handling of TTS service errors"""
        mock_synthesize.side_effect = TTSServiceError("Service unavailable")

        request_data = {
            "text": "Hello world",
            "language": "en"
        }

        response = client.post("/api/tts", json=request_data)

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert "TTS_SERVICE_ERROR" in data["error"]["code"]

    @patch('app.api.routes.tts.synthesize_speech', new_callable=AsyncMock)
    def test_tts_endpoint_unexpected_error(self, mock_synthesize):
        """Test handling of unexpected TTS errors"""
        mock_synthesize.side_effect = Exception("Unexpected error")

        request_data = {
            "text": "Hello world",
            "language": "en"
        }

        response = client.post("/api/tts", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "TTS_GENERATION_FAILED" in data["error"]["code"]

    def test_tts_endpoint_empty_text(self):
        """Test with empty text - returns 422 validation error"""
        request_data = {
            "text": "",
            "language": "en"
        }

        response = client.post("/api/tts", json=request_data)
        assert response.status_code == 422

    def test_tts_endpoint_invalid_language(self):
        """Test with invalid language code - returns 422 validation error"""
        request_data = {
            "text": "Hello world",
            "language": "fr"
        }

        response = client.post("/api/tts", json=request_data)
        assert response.status_code == 422

    def test_tts_endpoint_text_too_long(self):
        """Test with text exceeding limit - returns 400 bad request"""
        long_text = "A" * 100001
        request_data = {
            "text": long_text,
            "language": "en"
        }

        response = client.post("/api/tts", json=request_data)
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "TEXT_TOO_LONG" in data["error"]["code"]

    @patch('app.api.routes.tts.synthesize_speech', new_callable=AsyncMock)
    def test_tts_endpoint_audio_metadata(self, mock_synthesize):
        """Test that TTS response includes correct audio metadata"""
        mock_synthesize.return_value = (
            '/fake/path/test.mp3',
            {
                "language": "en",
                "voice": "en-US-AriaNeural",
                "text_length": 12,
                "file_size_bytes": 4096,
                "duration_ms": 75,
                "filename": "tts_en_metadata999.mp3",
                "content_type": "audio/mpeg"
            }
        )

        request_data = {
            "text": "Hello world",
            "language": "en"
        }

        response = client.post("/api/tts", json=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert "audio_url" in data
        assert "filename" in data
        assert "file_size_bytes" in data
        assert "content_type" in data
        assert data["content_type"] == "audio/mpeg"
        assert data["file_size_bytes"] == 4096


class TestTTSServiceGlobalInstance:
    """Test global TTS service instance"""

    def test_tts_service_global_instance(self):
        """Test that global TTS service instance works"""
        from app.services.tts_service import synthesize_speech, tts_service

        assert tts_service is not None
        assert callable(synthesize_speech)

    def test_synthesize_speech_is_async(self):
        """Test that synthesize_speech is an async function"""
        import inspect
        assert inspect.iscoroutinefunction(synthesize_speech)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
