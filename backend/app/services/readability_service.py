"""
Readability analysis service.
Calculates objective readability metrics for text comparison and analysis.
"""

import time
import re
from typing import Dict, Any, Optional, Tuple
import textstat
from app.core.logging import get_logger
from app.utils import text_utils

logger = get_logger(__name__)


def normalize_text_for_readability(text: str) -> str:
    """
    Normalize text for readability analysis by removing problematic elements.

    textstat's CMU dictionary has limitations and throws KeyError on:
    - Numbers: "18", "2,50,000"
    - Proper nouns: "Aadhaar", "Kannada"
    - Special characters: "₹2,50,000"

    This function aggressively removes problematic content to allow calculations.

    Args:
        text: Text to normalize

    Returns:
        Text cleaned for readability analysis
    """
    # Remove numbers
    text = re.sub(r'\b\d+(?:[.,]\d+)*\b', '', text)

    # Remove currency symbols and other special symbols
    text = re.sub(r'[₹$€¥£]', '', text)

    # Remove punctuation that might interfere
    text = re.sub(r'[\'"(){}[\]<>]', '', text)

    # Remove words starting with capitals (likely proper nouns not in CMU dict)
    # Keep only lowercase words and common contractions
    words = text.split()
    cleaned_words = []
    for word in words:
        # Keep word if it's lowercase, is a common word, or is a contraction
        if word and (word[0].islower() or "'" in word or '-' in word):
            cleaned_words.append(word)
    text = ' '.join(cleaned_words)

    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def count_syllables(text: str) -> int:
    """
    Count syllables in text using textstat.

    Args:
        text: Text to analyze

    Returns:
        Approximate syllable count
    """
    if not text or not text.strip():
        return 0
    try:
        return textstat.syllable_count(text)
    except Exception as e:
        logger.warning(f"Error counting syllables: {str(e)}")
        return 0


def calculate_flesch_reading_ease(text: str) -> Optional[float]:
    """
    Calculate Flesch Reading Ease score.

    Higher scores = easier to read (0-100)
    - 90-100: Very easy (5th grade)
    - 60-70: Standard (8th-9th grade)
    - 0-30: Very difficult (college/graduate)

    Args:
        text: Text to analyze

    Returns:
        Flesch Reading Ease score or None if calculation fails
    """
    if not text or not text.strip():
        return None

    try:
        # Normalize text to avoid textstat KeyError on numbers
        normalized_text = normalize_text_for_readability(text)
        if not normalized_text or not normalized_text.strip():
            return None
        # textstat returns float with 2 decimal places
        score = textstat.flesch_reading_ease(normalized_text)
        # Clamp to 0-100 range (textstat can return values outside this)
        return max(0.0, min(100.0, score))
    except KeyError as e:
        # textstat CMU dict lookup failed (unknown word/number)
        logger.debug(f"Flesch Reading Ease KeyError (CMU dict lookup): {str(e)}")
        return None
    except Exception as e:
        logger.warning(f"Error calculating Flesch Reading Ease: {str(e)}")
        return None


def calculate_flesch_kincaid_grade(text: str) -> Optional[float]:
    """
    Calculate Flesch-Kincaid Grade Level.

    Returns a US grade level (1-12+)
    - 5 = Grade 5 (typically 10-11 years old)
    - 9 = Grade 9 (typically 14-15 years old)
    - 13+ = College/graduate level

    Args:
        text: Text to analyze

    Returns:
        Flesch-Kincaid Grade Level or None if calculation fails
    """
    if not text or not text.strip():
        return None

    try:
        # Normalize text to avoid textstat KeyError on numbers
        normalized_text = normalize_text_for_readability(text)
        if not normalized_text or not normalized_text.strip():
            return None
        # textstat returns float with 2 decimal places
        grade = textstat.flesch_kincaid_grade(normalized_text)
        # Clamp to reasonable range (0-18)
        return max(0.0, min(18.0, grade))
    except KeyError as e:
        # textstat CMU dict lookup failed (unknown word/number)
        logger.debug(f"Flesch-Kincaid KeyError (CMU dict lookup): {str(e)}")
        return None
    except Exception as e:
        logger.warning(f"Error calculating Flesch-Kincaid Grade: {str(e)}")
        return None


def analyze_text_readability(text: str) -> Dict[str, Any]:
    """
    Analyze readability metrics for a single text.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with readability metrics:
        - word_count: Number of words
        - sentence_count: Number of sentences
        - character_count: Number of characters
        - syllable_count: Number of syllables
        - average_sentence_length: Words per sentence
        - flesch_reading_ease: Flesch Reading Ease (0-100)
        - flesch_kincaid_grade: Grade level
    """
    if not text:
        return {
            "word_count": 0,
            "sentence_count": 0,
            "character_count": 0,
            "syllable_count": 0,
            "average_sentence_length": 0.0,
            "flesch_reading_ease": None,
            "flesch_kincaid_grade": None,
        }

    word_count = text_utils.count_words(text)
    sentence_count = text_utils.count_sentences(text)
    character_count = len(text)
    syllable_count = count_syllables(text)

    # Handle edge cases
    if sentence_count == 0:
        avg_sentence_length = 0.0
    else:
        avg_sentence_length = word_count / sentence_count

    flesch_ease = calculate_flesch_reading_ease(text)
    flesch_grade = calculate_flesch_kincaid_grade(text)

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "character_count": character_count,
        "syllable_count": syllable_count,
        "average_sentence_length": round(avg_sentence_length, 2),
        "flesch_reading_ease": round(flesch_ease, 1) if flesch_ease is not None else None,
        "flesch_kincaid_grade": round(flesch_grade, 1) if flesch_grade is not None else None,
    }


def compare_readability(
    original_text: str,
    simplified_text: str,
    target_grade_level: int = 5,
) -> Dict[str, Any]:
    """
    Compare readability metrics between original and simplified text.

    Args:
        original_text: Original document text
        simplified_text: Simplified document text
        target_grade_level: Target reading grade level (1-12)

    Returns:
        Dictionary with original metrics, simplified metrics, and comparison
    """
    start_time = time.time()

    # Analyze both texts
    original_metrics = analyze_text_readability(original_text)
    simplified_metrics = analyze_text_readability(simplified_text)

    # Calculate improvements
    original_grade = original_metrics.get("flesch_kincaid_grade")
    simplified_grade = simplified_metrics.get("flesch_kincaid_grade")

    original_ease = original_metrics.get("flesch_reading_ease")
    simplified_ease = simplified_metrics.get("flesch_reading_ease")

    # Grade improvement (positive = better)
    if original_grade is not None and simplified_grade is not None:
        grade_improvement = original_grade - simplified_grade
    else:
        grade_improvement = 0.0

    # Reading ease improvement (positive = better)
    if original_ease is not None and simplified_ease is not None:
        ease_improvement = simplified_ease - original_ease
    else:
        ease_improvement = 0.0

    # Sentence length reduction (positive = shorter sentences)
    original_sent_len = original_metrics.get("average_sentence_length", 0.0)
    simplified_sent_len = simplified_metrics.get("average_sentence_length", 0.0)
    sent_reduction = original_sent_len - simplified_sent_len

    # Target achievement check
    target_achieved = False
    if simplified_grade is not None:
        target_achieved = simplified_grade <= target_grade_level

    processing_time_ms = int((time.time() - start_time) * 1000)

    return {
        "original": original_metrics,
        "simplified": simplified_metrics,
        "comparison": {
            "grade_level_improvement": round(grade_improvement, 1),
            "reading_ease_improvement": round(ease_improvement, 1),
            "sentence_length_reduction": round(sent_reduction, 2),
            "target_grade_level": target_grade_level,
            "simplified_grade_level": simplified_grade,
            "target_achieved": target_achieved,
        },
        "processing_time_ms": processing_time_ms,
    }
