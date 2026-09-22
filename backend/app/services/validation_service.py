"""
Fact preservation validation service.
Validates that critical factual information is preserved in simplified text.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from app.schemas.simplification import PreservedFact
from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_critical_facts(text: str) -> List[PreservedFact]:
    """
    Extract critical factual information from text.

    Args:
        text: Source text to extract facts from

    Returns:
        List of PreservedFact objects
    """
    facts = []

    # Extract dates (e.g., "31 December 2026", "2026-12-31", "12/31/2026")
    date_patterns = [
        r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        r'before\s+(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
        r'by\s+(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
        r'on\s+(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})'
    ]

    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(1)
            source_text = extract_surrounding_text(text, match.start(), match.end(), 50)
            facts.append(PreservedFact(
                fact_type="deadline",
                value=value,
                source_text=source_text,
                preserved_in_simplified=False
            ))

    # Extract Indian currency amounts (e.g., "₹2,50,000", "Rs. 2,50,000", "INR 2,50,000")
    # CRITICAL: Must have currency context (₹, Rs, INR, etc.) or explicit rupee/lakh/crore
    currency_patterns = [
        r'[₹]\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)',  # ₹2,50,000
        r'Rs\.\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)',  # Rs. 2,50,000
        r'INR\s+(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)',  # INR 2,50,000
        r'(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)\s*(?:rupees|lakh|crore)',  # 2,50,000 rupees
    ]

    for pattern in currency_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(1)
            source_text = extract_surrounding_text(text, match.start(), match.end(), 50)
            facts.append(PreservedFact(
                fact_type="money",
                value=value,
                source_text=source_text,
                preserved_in_simplified=False
            ))

    # Extract percentages (e.g., "50%", "50 percent", "50 per cent")
    percent_patterns = [
        r'(\d{1,3}(?:\.\d{1,2})?)%',
        r'(\d{1,3}(?:\.\d{1,2})?)\s+percent',
        r'(\d{1,3}(?:\.\d{1,2})?)\s+per\s+cent'
    ]

    for pattern in percent_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(1) + "%"
            source_text = extract_surrounding_text(text, match.start(), match.end(), 50)
            facts.append(PreservedFact(
                fact_type="percentage",
                value=value,
                source_text=source_text,
                preserved_in_simplified=False
            ))

    # Extract ages (e.g., "18 years old", "age 18", "minimum age of 18 years")
    age_patterns = [
        r'(\d{1,3})\s*years?\s*(?:old|of\s+age|or\s+older|or\s+above)',
        r'age\s+of?\s*(\d{1,3})\s*years?',
        r'minimum\s+age\s+of?\s*(\d{1,3})\s*years?',
        r'at\s+least\s+(\d{1,3})\s*years?\s*old'
    ]

    for pattern in age_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = f"{match.group(1)} years"
            source_text = extract_surrounding_text(text, match.start(), match.end(), 50)
            facts.append(PreservedFact(
                fact_type="age",
                value=value,
                source_text=source_text,
                preserved_in_simplified=False
            ))

    # Extract quantities/numerical values
    quantity_patterns = [
        r'(\d{1,6}(?:,\d{3})*(?:\.\d+)?)\s*(?:units?|items?|applications?|forms?)',
        r'minimum\s+of\s+(\d{1,6}(?:,\d{3})*(?:\.\d+)?)\s+(?!years)',
        r'at\s+least\s+(\d{1,6}(?:,\d{3})*(?:\.\d+)?)\s+(?!years)'
    ]

    for pattern in quantity_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(1)
            source_text = extract_surrounding_text(text, match.start(), match.end(), 50)
            facts.append(PreservedFact(
                fact_type="quantity",
                value=value,
                source_text=source_text,
                preserved_in_simplified=False
            ))

    # Remove duplicates (same value and type)
    unique_facts = []
    seen = set()
    for fact in facts:
        key = (fact.value, fact.fact_type)
        if key not in seen:
            seen.add(key)
            unique_facts.append(fact)

    return unique_facts


def extract_surrounding_text(text: str, start: int, end: int, context_chars: int = 50) -> str:
    """
    Extract text around a given position for context.

    Args:
        text: Full text
        start: Start index
        end: End index
        context_chars: Number of characters before/after to include

    Returns:
        Context text with the matched portion
    """
    context_start = max(0, start - context_chars)
    context_end = min(len(text), end + context_chars)

    # Find sentence boundaries for cleaner context
    result = text[context_start:context_end]

    # Clean up if we cut in middle of a word
    if context_start > 0 and text[context_start].isalnum():
        # Find previous space or punctuation
        while context_start > 0 and text[context_start - 1].isalnum():
            context_start -= 1
        result = text[context_start:context_end]

    if context_end < len(text) and text[context_end - 1].isalnum():
        # Find next space or punctuation
        while context_end < len(text) and text[context_end].isalnum():
            context_end += 1
        result = text[context_start:context_end]

    return result.strip()


def validate_fact_preservation(original_text: str, simplified_text: str) -> Tuple[List[PreservedFact], List[str]]:
    """
    Validate that critical facts are preserved in simplified text.

    Args:
        original_text: Source text
        simplified_text: Simplified text

    Returns:
        Tuple of (preserved_facts, validation_failures)
    """
    facts = extract_critical_facts(original_text)
    validation_failures = []

    for fact in facts:
        # Check if fact value appears in simplified text
        fact_in_simplified = False

        # For dates, normalize and compare
        if fact.fact_type == "deadline":
            # Try exact match first
            if fact.value in simplified_text:
                fact_in_simplified = True
            else:
                # Try normalizing date formats
                normalized_fact_date = normalize_date_format(fact.value)

                # Look for the normalized date or similar date formats in simplified text
                # Try to find matching normalized dates
                date_patterns = [
                    r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
                    r'(\d{4}-\d{2}-\d{2})',
                    r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                    r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}',
                ]

                for pattern in date_patterns:
                    for match in re.finditer(pattern, simplified_text, re.IGNORECASE):
                        found_date_str = match.group(1) if match.lastindex else match.group(0)
                        normalized_found_date = normalize_date_format(found_date_str)

                        # Compare normalized dates
                        if normalized_fact_date == normalized_found_date:
                            fact_in_simplified = True
                            break
                    if fact_in_simplified:
                        break

        # For money, check for currency symbols and numbers
        elif fact.fact_type == "money":
            # Extract numeric value
            numeric_value = re.sub(r'[^\d.,]', '', fact.value)
            # Normalize by removing commas for comparison
            normalized_numeric = numeric_value.replace(',', '')

            # Look for the value in simplified text
            if re.search(f'\\b{re.escape(numeric_value)}\\b', simplified_text):
                fact_in_simplified = True
            # Also try without commas
            elif re.search(f'\\b{normalized_numeric}\\b', simplified_text):
                fact_in_simplified = True
            # Also check for Indian currency symbol near the number
            elif re.search(f'[₹Rs\\.]?\\s*{re.escape(numeric_value)}', simplified_text):
                fact_in_simplified = True
            # Try alternative formats (with/without commas)
            elif re.search(f'[₹Rs\\.]?\\s*{normalized_numeric}', simplified_text):
                fact_in_simplified = True

        # For percentages, ages, quantities - check for numbers
        elif fact.fact_type in ["percentage", "age", "quantity"]:
            # Extract the numeric part
            numeric_match = re.search(r'(\d+(?:\.\d+)?)', fact.value)
            if numeric_match:
                numeric_value = numeric_match.group(1)
                if re.search(f'\\b{numeric_value}\\b', simplified_text):
                    fact_in_simplified = True

        fact.preserved_in_simplified = fact_in_simplified

        if not fact_in_simplified:
            validation_failures.append(f"Fact not preserved: {fact.fact_type} '{fact.value}'")

    return facts, validation_failures


def normalize_date_format(date_str: str) -> str:
    """
    Normalize date to standard ISO format (YYYY-MM-DD) for comparison.

    Args:
        date_str: Date string in various formats

    Returns:
        Normalized date string in YYYY-MM-DD format, or original if parsing fails
    """
    try:
        # Try to parse common formats
        date_formats = [
            "%d %B %Y",      # 31 December 2026
            "%d %b %Y",      # 31 Dec 2026
            "%Y-%m-%d",      # 2026-12-31
            "%d-%m-%Y",      # 31-12-2026
            "%d/%m/%Y",      # 31/12/2026
            "%m/%d/%Y",      # 12/31/2026
            "%B %d, %Y",     # December 31, 2026
            "%b %d, %Y",     # Dec 31, 2026
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return date_str  # Return original if parsing fails
    except Exception:
        return date_str


def normalize_date_format_in_text(text: str) -> str:
    """
    Normalize dates in text for comparison.
    Extracts and returns normalized dates from text.

    Args:
        text: Text containing dates

    Returns:
        Text with normalized date representations
    """
    # Extract all date patterns and normalize them
    date_patterns = [
        r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}',
    ]

    normalized_dates = []
    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            date_str = match.group(1) if match.lastindex else match.group(0)
            normalized_dates.append(normalize_date_format(date_str))

    return " ".join(normalized_dates) if normalized_dates else ""


def validate_simplification_quality(original_text: str, simplified_text: str) -> List[str]:
    """
    Perform basic quality validation of simplification.

    Args:
        original_text: Original text
        simplified_text: Simplified text

    Returns:
        List of quality issues found
    """
    issues = []

    # Check if simplified text is too short (potential content loss)
    # But allow very short simplifications if original is also very short
    if len(original_text) > 50 and len(simplified_text) < len(original_text) * 0.2:
        issues.append("Simplified text is suspiciously short (possible content loss)")

    # Check if simplified text is too similar (no simplification)
    # Only apply for texts longer than 200 characters to avoid false positives
    if len(original_text) > 200 and len(simplified_text) > len(original_text) * 0.9:
        # Calculate actual similarity based on preserved facts and structure
        original_sentences = re.split(r'[.!?]+', original_text)
        simplified_sentences = re.split(r'[.!?]+', simplified_text)

        # If number of sentences hasn't changed much, might be too similar
        if len(simplified_sentences) <= len(original_sentences) * 1.2:
            # Count preserved fact numbers/dates
            facts = extract_critical_facts(original_text)
            preserved_count = 0
            for fact in facts:
                if fact.value in simplified_text:
                    preserved_count += 1

            # If most facts are preserved but text is similar length, that's OK
            if preserved_count < len(facts) * 0.5:
                issues.append("Simplified text is too similar to original (possible lack of simplification)")

    # Check for obvious hallucinations or changes
    original_words = set(re.findall(r'\b\w{4,}\b', original_text.lower()))
    simplified_words = set(re.findall(r'\b\w{4,}\b', simplified_text.lower()))

    # Look for added keywords that weren't in original
    added_keywords = simplified_words - original_words
    suspicious_keywords = {"free", "guaranteed", "immediately", "urgent", "special", "limited", "bonus", "only"}
    suspicious_added = added_keywords.intersection(suspicious_keywords)

    # Only flag if suspicious words constitute more than 5% of new words
    if suspicious_added and len(added_keywords) > 0:
        suspicious_ratio = len(suspicious_added) / max(1, len(added_keywords))
        if suspicious_ratio > 0.2:
            issues.append(f"Potentially hallucinated keywords added: {', '.join(suspicious_added)}")

    return issues


def validate_final_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the final simplification response.

    Args:
        response_data: Simplification response data

    Returns:
        Updated response with validation results
    """
    original_text = response_data.get("original_text", "")
    simplified_text = response_data.get("simplified_text", "")

    # Validate fact preservation
    preserved_facts, validation_failures = validate_fact_preservation(original_text, simplified_text)

    # Validate quality
    quality_issues = validate_simplification_quality(original_text, simplified_text)
    validation_failures.extend(quality_issues)

    # Update response data
    response_data["preserved_facts"] = preserved_facts
    response_data["validation_failures"] = validation_failures
    response_data["validation_passed"] = len(validation_failures) == 0

    # Calculate preservation statistics
    total_facts = len(preserved_facts)
    preserved_count = sum(1 for fact in preserved_facts if fact.preserved_in_simplified)

    if total_facts > 0:
        response_data["metadata"]["fact_preservation_rate"] = preserved_count / total_facts
    else:
        response_data["metadata"]["fact_preservation_rate"] = 1.0

    logger.info(f"Fact validation: {preserved_count}/{total_facts} facts preserved")

    if validation_failures:
        logger.warning(f"Validation issues found: {validation_failures}")

    return response_data
