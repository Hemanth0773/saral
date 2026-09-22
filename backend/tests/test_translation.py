"""
Tests for Translation Service (MILESTONE 9).
Tests cover translation service, API endpoints, and language translation functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import torch

from app.main import app
from app.services import translation_service
from app.schemas.translation import (
    TranslationRequest,
    TranslationResponse,
    BatchTranslationRequest,
    BatchTranslationResponse
)


client = TestClient(app)


class TestTranslationService:
    """Test translation service functionality"""

    def test_translation_service_singleton(self):
        """Test that translation service follows singleton pattern"""
        service1 = translation_service.TranslationService()
        service2 = translation_service.TranslationService()
        assert service1 is service2

    def test_language_code_mapping(self):
        """Test language code mapping for NLLB"""
        service = translation_service.TranslationService()
        assert service._get_nllb_language_code('en') == 'eng_Latn'
        assert service._get_nllb_language_code('kn') == 'kan_Knda'
        assert service._get_nllb_language_code('EN') == 'eng_Latn'  # Case insensitive
        assert service._get_nllb_language_code('KN') == 'kan_Knda'

    def test_same_language_translation(self):
        """Test translation when source and target are the same"""
        service = translation_service.TranslationService()
        text = "Hello world"

        # English to English
        translated, metadata = service.translate(text, 'en', 'en')
        assert translated == text
        assert metadata['source_language'] == 'en'
        assert metadata['target_language'] == 'en'
        assert metadata['character_count'] == len(text)
        assert metadata['translated_character_count'] == len(text)

        # Kannada to Kannada
        kannada_text = "ನಮಸ್ಕಾರ ಜಗತ"  # Some Kannada text
        translated, metadata = service.translate(kannada_text, 'kn', 'kn')
        assert translated == kannada_text

    @patch('torch.cuda.is_available')
    def test_model_loading_cpu_fallback(self, mock_cuda_available):
        """Test model loading falls back to CPU when GPU not available"""
        mock_cuda_available.return_value = False

        # Create new service instance to test loading
        with patch.object(translation_service.TranslationService, '_model', None):
            with patch.object(translation_service.TranslationService, '_tokenizer', None):
                service = translation_service.TranslationService()
                # Should not raise exception
                assert service._device == torch.device("cpu")

    def test_unsupported_language_raises_error(self):
        """Test that unsupported language raises error"""
        service = translation_service.TranslationService()
        with pytest.raises(translation_service.TranslationServiceError):
            service.translate("Hello", 'fr', 'en')  # French not supported

        with pytest.raises(translation_service.TranslationServiceError):
            service.translate("Hello", 'en', 'fr')  # French not supported

    def test_empty_text_raises_error(self):
        """Test that empty text raises error"""
        service = translation_service.TranslationService()
        with pytest.raises(translation_service.TranslationServiceError):
            service.translate("", 'en', 'kn')

        with pytest.raises(translation_service.TranslationServiceError):
            service.translate("   ", 'en', 'kn')  # Whitespace only

    @patch('app.services.translation_service.AutoTokenizer.from_pretrained')
    @patch('app.services.translation_service.AutoModelForSeq2SeqLM.from_pretrained')
    def test_model_loading_failure(self, mock_model_from_pretrained, mock_tokenizer_from_pretrained):
        """Test handling of model loading failure"""
        mock_tokenizer_from_pretrained.side_effect = Exception("Model not found")

        # Reset singleton state to force re-initialization
        translation_service.TranslationService._instance = None
        translation_service.TranslationService._model = None
        translation_service.TranslationService._tokenizer = None
        translation_service.TranslationService._device = None

        with pytest.raises(translation_service.TranslationModelNotLoadedError):
            translation_service.TranslationService()


class TestTranslationAPIEndpoint:
    """Test translation API endpoint"""

    def test_translate_endpoint_success_en_to_kn(self):
        """Test successful English to Kannada translation"""
        request_data = {
            "text": "Hello world",
            "source_language": "en",
            "target_language": "kn"
        }

        # Mock the translation service to return a predictable result
        with patch('app.api.routes.translation.translate_text') as mock_translate:
            mock_translate.return_value = (
                "ನಮಸ್ಕಾರ ಜಗತ",  # Mock Kannada translation
                {
                    "source_language": "en",
                    "target_language": "kn",
                    "model_used": "facebook/nllb-200-distilled-600M",
                    "character_count": 11,
                    "translated_character_count": 12
                }
            )

            response = client.post("/api/translate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["translated_text"] == "ನಮಸ್ಕಾರ ಜಗತ"
        assert data["source_language"] == "en"
        assert data["target_language"] == "kn"
        assert data["model_used"] == "facebook/nllb-200-distilled-600M"
        assert data["character_count"] == 11
        assert data["translated_character_count"] == 12

    def test_translate_endpoint_success_kn_to_en(self):
        """Test successful Kannada to English translation"""
        request_data = {
            "text": "ನಮಸ್ಕಾರ ಜಗತ",
            "source_language": "kn",
            "target_language": "en"
        }

        # Mock the translation service
        with patch('app.api.routes.translation.translate_text') as mock_translate:
            mock_translate.return_value = (
                "Hello world",
                {
                    "source_language": "kn",
                    "target_language": "en",
                    "model_used": "facebook/nllb-200-distilled-600M",
                    "character_count": 12,
                    "translated_character_count": 11
                }
            )

            response = client.post("/api/translate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["translated_text"] == "Hello world"
        assert data["source_language"] == "kn"
        assert data["target_language"] == "en"

    def test_translate_endpoint_same_language(self):
        """Test translation when source and target are the same"""
        request_data = {
            "text": "Hello world",
            "source_language": "en",
            "target_language": "en"
        }

        with patch('app.api.routes.translation.translate_text') as mock_translate:
            mock_translate.return_value = (
                "Hello world",
                {
                    "source_language": "en",
                    "target_language": "en",
                    "model_used": "facebook/nllb-200-distilled-600M",
                    "character_count": 11,
                    "translated_character_count": 11
                }
            )

            response = client.post("/api/translate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["translated_text"] == "Hello world"

    def test_translate_endpoint_empty_text(self):
        """Test translation with empty text"""
        request_data = {
            "text": "",
            "source_language": "en",
            "target_language": "kn"
        }

        response = client.post("/api/translate", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_translate_endpoint_invalid_language(self):
        """Test translation with invalid language code"""
        request_data = {
            "text": "Hello world",
            "source_language": "fr",  # Not supported
            "target_language": "en"
        }

        response = client.post("/api/translate", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_translate_endpoint_text_too_long(self):
        """Test translation with text exceeding limit"""
        long_text = "A" * 100001  # Exceeds MAX_DOCUMENT_LENGTH
        request_data = {
            "text": long_text,
            "source_language": "en",
            "target_language": "kn"
        }

        response = client.post("/api/translate", json=request_data)
        assert response.status_code == 400  # Bad request - too long
        data = response.json()
        assert data["success"] is False
        assert "TEXT_TOO_LONG" in data["error"]["code"]

    def test_translate_endpoint_service_error(self):
        """Test handling of translation service errors"""
        request_data = {
            "text": "Hello world",
            "source_language": "en",
            "target_language": "kn"
        }

        with patch('app.api.routes.translation.translate_text') as mock_translate:
            mock_translate.side_effect = translation_service.TranslationServiceError("Service unavailable")

            response = client.post("/api/translate", json=request_data)

        assert response.status_code == 503  # Service unavailable
        data = response.json()
        assert data["success"] is False
        assert "TRANSLATION_SERVICE_ERROR" in data["error"]["code"]

    def test_translate_endpoint_unexpected_error(self):
        """Test handling of unexpected translation errors"""
        request_data = {
            "text": "Hello world",
            "source_language": "en",
            "target_language": "kn"
        }

        with patch('app.api.routes.translation.translate_text') as mock_translate:
            mock_translate.side_effect = Exception("Unexpected error")

            response = client.post("/api/translate", json=request_data)

        assert response.status_code == 500  # Internal server error
        data = response.json()
        assert data["success"] is False
        assert "TRANSLATION_FAILED" in data["error"]["code"]

    def test_batch_translate_endpoint_success(self):
        """Test successful batch translation"""
        request_data = {
            "texts": ["Hello", "World"],
            "source_language": "en",
            "target_language": "kn"
        }

        with patch('app.api.routes.translation.batch_translate_texts') as mock_batch_translate:
            mock_batch_translate.return_value = [
                ("ನಮಸ್ಕಾರ", {
                    "source_language": "en",
                    "target_language": "kn",
                    "model_used": "facebook/nllb-200-distilled-600M",
                    "character_count": 5,
                    "translated_character_count": 6
                }),
                ("ಲೋಕ", {
                    "source_language": "en",
                    "target_language": "kn",
                    "model_used": "facebook/nllb-200-distilled-600M",
                    "character_count": 5,
                    "translated_character_count": 4
                })
            ]

            response = client.post("/api/translate/batch", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["batch_size"] == 2
        assert len(data["translations"]) == 2
        assert data["translations"][0]["translated_text"] == "ನಮಸ್ಕಾರ"
        assert data["translations"][1]["translated_text"] == "ಲೋಕ"

    def test_batch_translate_endpoint_empty_list(self):
        """Test batch translation with empty list"""
        request_data = {
            "texts": [],
            "source_language": "en",
            "target_language": "kn"
        }

        response = client.post("/api/translate/batch", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_batch_translate_endpoint_too_many_texts(self):
        """Test batch translation exceeding limit"""
        request_data = {
            "texts": ["Text"] * 101,  # Exceeds limit of 100
            "source_language": "en",
            "target_language": "kn"
        }

        response = client.post("/api/translate/batch", json=request_data)
        assert response.status_code == 400  # Bad request
        data = response.json()
        assert data["success"] is False
        assert "BATCH_SIZE_TOO_LARGE" in data["error"]["code"]

    def test_batch_translate_endpoint_individual_text_too_long(self):
        """Test batch translation with individual text too long"""
        request_data = {
            "texts": ["Short", "A" * 100001],  # Second text too long
            "source_language": "en",
            "target_language": "kn"
        }

        response = client.post("/api/translate/batch", json=request_data)
        assert response.status_code == 400  # Bad request
        data = response.json()
        assert data["success"] is False
        assert "TEXT_TOO_LONG" in data["error"]["code"]

    def test_batch_translate_endpoint_service_error(self):
        """Test handling of batch translation service errors"""
        request_data = {
            "texts": ["Hello", "World"],
            "source_language": "en",
            "target_language": "kn"
        }

        with patch('app.api.routes.translation.batch_translate_texts') as mock_batch_translate:
            mock_batch_translate.side_effect = translation_service.TranslationServiceError("Service unavailable")

            response = client.post("/api/translate/batch", json=request_data)

        assert response.status_code == 503  # Service unavailable
        data = response.json()
        assert data["success"] is False
        assert "TRANSLATION_SERVICE_ERROR" in data["error"]["code"]

    def test_batch_translate_endpoint_unexpected_error(self):
        """Test handling of unexpected batch translation errors"""
        request_data = {
            "texts": ["Hello", "World"],
            "source_language": "en",
            "target_language": "kn"
        }

        with patch('app.api.routes.translation.batch_translate_texts') as mock_batch_translate:
            mock_batch_translate.side_effect = Exception("Unexpected error")

            response = client.post("/api/translate/batch", json=request_data)

        assert response.status_code == 500  # Internal server error
        data = response.json()
        assert data["success"] is False
        assert "TRANSLATION_FAILED" in data["error"]["code"]


class TestTranslationIntegration:
    """Integration tests for translation functionality"""

    def test_translation_preserves_numbers_and_dates(self):
        """Test that translation preserves numbers and dates (when they remain the same)"""
        # This test assumes the mock translation preserves the text as-is for same-language
        request_data = {
            "text": "The deadline is 31 December 2026. Amount is ₹2,50,000.",
            "source_language": "en",
            "target_language": "en"  # Same language to preserve exact text
        }

        with patch('app.api.routes.translation.translate_text') as mock_translate:
            mock_translate.return_value = (
                request_data["text"],  # Exact same text for same-language translation
                {
                    "source_language": "en",
                    "target_language": "en",
                    "model_used": "facebook/nllb-200-distilled-600M",
                    "character_count": len(request_data["text"]),
                    "translated_character_count": len(request_data["text"])
                }
            )

            response = client.post("/api/translate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Verify numbers and dates are preserved
        assert "31 December 2026" in data["translated_text"]
        assert "₹2,50,000" in data["translated_text"]

    def test_translation_service_global_instance(self):
        """Test that global translation service instance works"""
        from app.services.translation_service import translate_text, translation_service

        # Test that we can access the global instance
        assert translation_service is not None

        # Test the convenience function exists
        assert callable(translate_text)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])