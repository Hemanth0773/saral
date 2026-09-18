"""
Text processing utilities for document extraction.
Handles text cleaning, analysis, and metadata extraction.
"""

import re
from typing import Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


def clean_text(text: str) -> str:
    """
    Clean extracted text by removing extra whitespace and normalizing.

    Args:
        text: Raw extracted text

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # Remove multiple newlines, keep single newlines
    text = re.sub(r'\n\n+', '\n', text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def count_words(text: str) -> int:
    """
    Count words in text.

    Args:
        text: Text to analyze

    Returns:
        Word count
    """
    if not text:
        return 0
    return len(text.split())


def count_sentences(text: str) -> int:
    """
    Estimate sentence count (basic heuristic).

    Args:
        text: Text to analyze

    Returns:
        Approximate sentence count
    """
    if not text:
        return 0
    # Count sentences ending with . ! or ?
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])


def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """
    Estimate reading time in minutes.

    Args:
        text: Text to analyze
        words_per_minute: Average reading speed (default 200)

    Returns:
        Estimated reading time in minutes
    """
    word_count = count_words(text)
    reading_time = max(1, word_count // words_per_minute)
    return reading_time


def truncate_text(text: str, max_length: int = 50000) -> tuple[str, bool]:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length in characters

    Returns:
        Tuple of (truncated_text, was_truncated)
    """
    if len(text) <= max_length:
        return text, False

    # Truncate at word boundary
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.9:  # If space is close to end, use it
        truncated = truncated[:last_space]

    return truncated + "...", True


def detect_language_heuristic(text: str) -> str:
    """
    Simple language detection heuristic.
    Returns 'en' for English (ASCII-heavy), or 'other' for non-English.

    Args:
        text: Text to analyze

    Returns:
        Language code ('en', 'kn', 'hi', 'ta', 'te', 'ml', or 'other')
    """
    if not text:
        return "en"

    # Count ASCII vs non-ASCII characters
    ascii_count = sum(1 for c in text if ord(c) < 128)
    total_count = len(text)

    if total_count == 0:
        return "en"

    ascii_ratio = ascii_count / total_count

    # If mostly ASCII, assume English
    if ascii_ratio > 0.8:
        return "en"

    # Check for specific Unicode ranges (simplified)
    # Kannada: U+0C80 – U+0CFF
    # Hindi: U+0900 – U+097F
    # Tamil: U+0B80 – U+0BFF
    # Telugu: U+0C00 – U+0C7F
    # Malayalam: U+0D00 – U+0D7F

    kannada_count = sum(1 for c in text if 0xC80 <= ord(c) <= 0xCFF)
    hindi_count = sum(1 for c in text if 0x900 <= ord(c) <= 0x97F)
    tamil_count = sum(1 for c in text if 0xB80 <= ord(c) <= 0xBFF)
    telugu_count = sum(1 for c in text if 0xC00 <= ord(c) <= 0xC7F)
    malayalam_count = sum(1 for c in text if 0xD00 <= ord(c) <= 0xD7F)

    # Return most common detected language
    lang_counts = {
        "kn": kannada_count,
        "hi": hindi_count,
        "ta": tamil_count,
        "te": telugu_count,
        "ml": malayalam_count,
    }

    max_lang = max(lang_counts, key=lang_counts.get)
    if lang_counts[max_lang] > 0:
        return max_lang

    return "other"


def extract_metadata(text: str, filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract metadata from text.

    Args:
        text: Text to analyze
        filename: Original filename if available

    Returns:
        Dictionary with metadata
    """
    return {
        "word_count": count_words(text),
        "sentence_count": count_sentences(text),
        "character_count": len(text),
        "estimated_reading_time_minutes": estimate_reading_time(text),
        "language": detect_language_heuristic(text),
        "has_numbers": bool(re.search(r'\d', text)),
        "has_urls": bool(re.search(r'https?://', text)),
        "has_emails": bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)),
    }


def remove_extra_whitespace(text: str) -> str:
    """
    Remove extra whitespace from text.

    Args:
        text: Text to clean

    Returns:
        Text with normalized whitespace
    """
    # Replace tabs with spaces
    text = text.replace('\t', ' ')
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    # Preserve single newlines but remove multiple
    text = re.sub(r'\n {2,}', '\n', text)
    return text.strip()
