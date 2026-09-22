"""
Translation service using Facebook's NLLB model for English-Kannada translation.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Union
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.translation import (
    TranslationRequest,
    TranslationResponse,
    BatchTranslationRequest,
    BatchTranslationResponse
)

logger = get_logger(__name__)


class TranslationServiceError(Exception):
    """Base exception for translation service errors"""
    pass


class TranslationModelNotLoadedError(TranslationServiceError):
    """Exception raised when translation model fails to load"""
    pass


class TranslationService:
    """Translation service using NLLB model for language translation."""

    _instance: Optional['TranslationService'] = None
    _model: Optional[AutoModelForSeq2SeqLM] = None
    _tokenizer: Optional[AutoTokenizer] = None
    _device: Optional[torch.device] = None

    # NLLB model constants
    MODEL_NAME = "facebook/nllb-200-distilled-600M"

    # Language code mapping for NLLB (ISO 639-3 codes)
    LANGUAGE_CODES = {
        'en': 'eng_Latn',  # English
        'kn': 'kan_Knda'   # Kannada
    }

    def __new__(cls) -> 'TranslationService':
        """Singleton pattern to ensure model is loaded only once."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize translation service and load model if not already loaded."""
        if self._model is None or self._tokenizer is None:
            self._load_model()

    def _load_model(self) -> None:
        """Load the NLLB model and tokenizer."""
        try:
            logger.info(f"Loading NLLB translation model: {self.MODEL_NAME}")
            start_time = time.time()

            # Determine device (GPU if available, else CPU)
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"Using device: {self._device}")

            # Load tokenizer and model
            # If these fail, we should raise our specific TranslationModelNotLoadedError
            self._tokenizer = self._safe_tokenizer_load(self.MODEL_NAME)
            self._model = self._safe_model_load(self.MODEL_NAME)

            # Move model to device
            self._model.to(self._device)

            load_time = time.time() - start_time
            logger.info(f"NLLB model loaded successfully in {load_time:.2f} seconds")

        except TranslationModelNotLoadedError:
            # Re-raise our specific error
            raise
        except Exception as e:
            error_msg = f"Failed to load NLLB translation model: {str(e)}"
            logger.error(error_msg)
            raise TranslationModelNotLoadedError(error_msg)

    def _safe_tokenizer_load(self, model_name: str) -> AutoTokenizer:
        """Safely load tokenizer and convert loading errors to TranslationModelNotLoadedError"""
        try:
            return AutoTokenizer.from_pretrained(model_name)
        except Exception as e:
            error_msg = f"Failed to load NLLB tokenizer: {str(e)}"
            logger.error(error_msg)
            raise TranslationModelNotLoadedError(error_msg)

    def _safe_model_load(self, model_name: str) -> AutoModelForSeq2SeqLM:
        """Safely load model and convert loading errors to TranslationModelNotLoadedError"""
        try:
            return AutoModelForSeq2SeqLM.from_pretrained(model_name)
        except Exception as e:
            error_msg = f"Failed to load NLLB model: {str(e)}"
            logger.error(error_msg)
            raise TranslationModelNotLoadedError(error_msg)

    def _get_nllb_language_code(self, lang_code: str) -> str:
        """
        Convert ISO 639-1 language code to NLLB language code.

        Args:
            lang_code: ISO 639-1 language code (e.g., 'en', 'kn')

        Returns:
            NLLB language code (e.g., 'eng_Latn', 'kan_Knda')
        """
        return self.LANGUAGE_CODES.get(lang_code.lower(), lang_code)

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> Tuple[str, Dict[str, any]]:
        """
        Translate text from source language to target language.

        Args:
            text: Text to translate
            source_language: Source language code (e.g., 'en', 'kn')
            target_language: Target language code (e.g., 'en', 'kn')

        Returns:
            Tuple of (translated_text, metadata_dict)

        Raises:
            TranslationServiceError: If translation fails
        """
        if not text or not text.strip():
            raise TranslationServiceError("Text must not be empty")

        # Validate languages
        source_lang = source_language.lower()
        target_lang = target_language.lower()

        if source_lang not in self.LANGUAGE_CODES:
            raise TranslationServiceError(f"Unsupported source language: {source_language}")

        if target_lang not in self.LANGUAGE_CODES:
            raise TranslationServiceError(f"Unsupported target language: {target_language}")

        # If source and target are the same, return original text
        if source_lang == target_lang:
            return text, {
                "source_language": source_lang,
                "target_language": target_lang,
                "model_used": self.MODEL_NAME,
                "character_count": len(text),
                "translated_character_count": len(text)
            }

        try:
            start_time = time.time()

            # Get NLLB language codes
            src_nllb_code = self._get_nllb_language_code(source_lang)
            tgt_nllb_code = self._get_nllb_language_code(target_lang)

            # Tokenize input text
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512  # NLLB model limit
            )

            # Move inputs to device
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            # Set target language for generation
            # For NLLB tokenizer, we need to get the language token ID
            forced_bos_token_id = self._tokenizer.convert_tokens_to_ids(tgt_nllb_code)
            if forced_bos_token_id is None or forced_bos_token_id == self._tokenizer.unk_token_id:
                raise TranslationServiceError(f"Target language code {tgt_nllb_code} not supported by tokenizer")

            # Generate translation
            with torch.no_grad():
                translated_tokens = self._model.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos_token_id,
                    max_length=512,
                    num_beams=5,
                    length_penalty=1.0,
                    early_stopping=True
                )

            # Decode translation
            translated_text = self._tokenizer.batch_decode(
                translated_tokens,
                skip_special_tokens=True
            )[0]

            translation_time = time.time() - start_time

            # Prepare metadata
            metadata = {
                "source_language": source_lang,
                "target_language": target_lang,
                "model_used": self.MODEL_NAME,
                "character_count": len(text),
                "translated_character_count": len(translated_text),
                "translation_time_ms": int(translation_time * 1000)
            }

            logger.info(
                f"Translation completed: {source_lang}->{target_lang} "
                f"({len(text)} chars -> {len(translated_text)} chars, "
                f"{metadata['translation_time_ms']}ms)"
            )

            return translated_text, metadata

        except Exception as e:
            error_msg = f"Translation failed: {str(e)}"
            logger.error(error_msg)
            raise TranslationServiceError(error_msg)

    def batch_translate(
        self,
        texts: List[str],
        source_language: str,
        target_language: str
    ) -> List[Tuple[str, Dict[str, any]]]:
        """
        Translate multiple texts from source language to target language.

        Args:
            texts: List of texts to translate
            source_language: Source language code (e.g., 'en', 'kn')
            target_language: Target language code (e.g., 'en', 'kn')

        Returns:
            List of tuples (translated_text, metadata_dict)

        Raises:
            TranslationServiceError: If batch translation fails
        """
        if not texts:
            raise TranslationServiceError("Texts list must not be empty")

        # Validate languages
        source_lang = source_language.lower()
        target_lang = target_language.lower()

        if source_lang not in self.LANGUAGE_CODES:
            raise TranslationServiceError(f"Unsupported source language: {source_language}")

        if target_lang not in self.LANGUAGE_CODES:
            raise TranslationServiceError(f"Unsupported target language: {target_language}")

        # If source and target are the same, return original texts
        if source_lang == target_lang:
            results = []
            for text in texts:
                metadata = {
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "model_used": self.MODEL_NAME,
                    "character_count": len(text),
                    "translated_character_count": len(text)
                }
                results.append((text, metadata))
            return results

        try:
            start_time = time.time()

            # Get NLLB language codes
            src_nllb_code = self._get_nllb_language_code(source_lang)
            tgt_nllb_code = self._get_nllb_language_code(target_lang)

            # Tokenize all texts
            inputs = self._tokenizer(
                texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )

            # Move inputs to device
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            # Set target language for generation
            # For NLLB tokenizer, we need to get the language token ID
            forced_bos_token_id = self._tokenizer.convert_tokens_to_ids(tgt_nllb_code)
            if forced_bos_token_id is None or forced_bos_token_id == self._tokenizer.unk_token_id:
                raise TranslationServiceError(f"Target language code {tgt_nllb_code} not supported by tokenizer")

            # Generate translations
            with torch.no_grad():
                translated_tokens = self._model.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos_token_id,
                    max_length=512,
                    num_beams=5,
                    length_penalty=1.0,
                    early_stopping=True
                )

            # Decode translations
            translated_texts = self._tokenizer.batch_decode(
                translated_tokens,
                skip_special_tokens=True
            )

            translation_time = time.time() - start_time

            # Prepare results with metadata
            results = []
            for i, (original_text, translated_text) in enumerate(zip(texts, translated_texts)):
                metadata = {
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "model_used": self.MODEL_NAME,
                    "character_count": len(original_text),
                    "translated_character_count": len(translated_text),
                    "translation_time_ms": int((translation_time * 1000) / len(texts)) if texts else 0
                }
                results.append((translated_text, metadata))

            logger.info(
                f"Batch translation completed: {len(texts)} texts "
                f"{source_lang}->{target_lang} in {translation_time*1000:.2f}ms"
            )

            return results

        except Exception as e:
            error_msg = f"Batch translation failed: {str(e)}"
            logger.error(error_msg)
            raise TranslationServiceError(error_msg)


# Global translation service instance
translation_service = TranslationService()


def translate_text(
    text: str,
    source_language: str,
    target_language: str
) -> Tuple[str, Dict[str, any]]:
    """
    Convenience function to translate text using the global translation service.

    Args:
        text: Text to translate
        source_language: Source language code
        target_language: Target language code

    Returns:
        Tuple of (translated_text, metadata_dict)
    """
    return translation_service.translate(text, source_language, target_language)


def batch_translate_texts(
    texts: List[str],
    source_language: str,
    target_language: str
) -> List[Tuple[str, Dict[str, any]]]:
    """
    Convenience function to batch translate texts using the global translation service.

    Args:
        texts: List of texts to translate
        source_language: Source language code
        target_language: Target language code

    Returns:
        List of tuples (translated_text, metadata_dict)
    """
    return translation_service.batch_translate(texts, source_language, target_language)