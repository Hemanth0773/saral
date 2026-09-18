"""
Document orchestration service.
Coordinates document extraction workflow and provides business logic.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.services import pdf_service, webpage_service
from app.utils import text_utils

logger = get_logger(__name__)


def generate_document_id() -> str:
    """
    Generate unique document ID.

    Returns:
        Document ID in format: doc_20260918_135941_a1b2c3d4
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_hash = uuid.uuid4().hex[:8]
    document_id = f"{settings.DOCUMENT_ID_PREFIX}_{timestamp}_{random_hash}"
    return document_id


def detect_language(text: str) -> str:
    """
    Detect language from text using heuristics.

    Args:
        text: Text to analyze

    Returns:
        Language code (en, kn, hi, ta, te, ml, or other)
    """
    try:
        language = text_utils.detect_language_heuristic(text)
        logger.debug(f"Detected language: {language}")
        return language
    except Exception as e:
        logger.warning(f"Language detection failed: {str(e)}, defaulting to 'en'")
        return "en"


def process_pdf_upload(
    file_content: bytes,
    original_filename: str,
    upload_dir: str
) -> Dict[str, Any]:
    """
    Process PDF file upload.

    Args:
        file_content: Binary file content
        original_filename: Original filename
        upload_dir: Directory to save temp file

    Returns:
        Dictionary with extraction results

    Raises:
        ValueError: If processing fails
    """
    document_id = generate_document_id()

    try:
        # Import here to avoid circular imports
        from app.utils.file_utils import save_uploaded_file, clean_temp_file

        # Save file
        file_path = save_uploaded_file(file_content, original_filename, upload_dir)
        logger.info(f"Processing PDF: {document_id}")

        try:
            # Extract text
            text, extraction_method, page_count = pdf_service.extract_text_from_pdf(file_path)

            # Clean text
            clean_text = text_utils.clean_text(text)

            # Detect language
            language = detect_language(clean_text)

            # Truncate if needed
            truncated_text, was_truncated = text_utils.truncate_text(clean_text)

            # Get metadata
            word_count = text_utils.count_words(clean_text)
            extracted_at = datetime.utcnow().isoformat() + "Z"

            result = {
                "success": True,
                "document_id": document_id,
                "filename": original_filename,
                "language": language,
                "page_count": page_count,
                "extraction_method": extraction_method,
                "text": truncated_text,
                "text_truncated": was_truncated,
                "metadata": {
                    "document_id": document_id,
                    "filename": original_filename,
                    "language": language,
                    "page_count": page_count,
                    "word_count": word_count,
                    "extraction_method": extraction_method,
                    "extracted_at": extracted_at,
                }
            }

            logger.info(f"PDF processed successfully: {document_id}")
            return result

        finally:
            # Always clean up temp file
            clean_temp_file(file_path)

    except Exception as e:
        logger.error(f"PDF processing failed for {document_id}: {str(e)}")
        raise ValueError(f"PDF processing failed: {str(e)}")


def process_url_input(url: str) -> Dict[str, Any]:
    """
    Process URL input and extract text.

    Args:
        url: URL to process

    Returns:
        Dictionary with extraction results

    Raises:
        ValueError: If processing fails
    """
    document_id = generate_document_id()

    try:
        logger.info(f"Processing URL: {document_id} - {url}")

        # Extract text
        text, status_code = webpage_service.extract_text_from_url(url)

        # Clean text
        clean_text = text_utils.clean_text(text)

        # Detect language
        language = detect_language(clean_text)

        # Truncate if needed
        truncated_text, was_truncated = text_utils.truncate_text(clean_text)

        # Get metadata
        word_count = text_utils.count_words(clean_text)
        extracted_at = datetime.utcnow().isoformat() + "Z"

        result = {
            "success": True,
            "document_id": document_id,
            "language": language,
            "extraction_method": "webpage",
            "text": truncated_text,
            "text_truncated": was_truncated,
            "source_url": url,
            "metadata": {
                "document_id": document_id,
                "filename": None,
                "language": language,
                "page_count": 1,
                "word_count": word_count,
                "extraction_method": "webpage",
                "extracted_at": extracted_at,
            }
        }

        logger.info(f"URL processed successfully: {document_id}")
        return result

    except Exception as e:
        logger.error(f"URL processing failed for {document_id}: {str(e)}")
        raise ValueError(f"URL processing failed: {str(e)}")


def get_error_response(error_code: str, message: str) -> Dict[str, Any]:
    """
    Generate standard error response.

    Args:
        error_code: Error code identifier
        message: Human-readable error message

    Returns:
        Error response dictionary
    """
    return {
        "success": False,
        "error": {
            "code": error_code,
            "message": message
        }
    }
