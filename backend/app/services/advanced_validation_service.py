"""
M7 Advanced Fact Validation Service.
Cross-validates facts across original, simplified, and structured documents.
Reuses validation_service fact extraction where appropriate.
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.schemas.validation import (
    CrossDocumentValidationResult,
    CrossDocumentValidationRequest,
    FactContradiction,
    FactPreservationDetail,
    FactType,
    ValidationStatus,
)
from app.services.validation_service import (
    extract_critical_facts,
    normalize_date_format,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


def map_fact_type_m5_to_m7(fact_type_m5: str) -> FactType:
    """Map M5 fact type strings to M7 FactType enum."""
    mapping = {
        "deadline": FactType.DEADLINE,
        "money": FactType.MONETARY_AMOUNT,
        "percentage": FactType.PERCENTAGE,
        "age": FactType.AGE,
        "quantity": FactType.QUANTITY,
        "date": FactType.DATE,
        "document": FactType.REQUIRED_DOCUMENT,
        "eligibility": FactType.ELIGIBILITY_REQUIREMENT,
        "condition": FactType.IMPORTANT_CONDITION,
        "contact": FactType.CONTACT_INFORMATION,
        "location": FactType.LOCATION,
        "organization": FactType.OTHER,
    }
    return mapping.get(fact_type_m5, FactType.OTHER)


def validate_cross_document(
    original_text: str,
    simplified_text: Optional[str] = None,
    structured_information: Optional[Dict[str, Any]] = None,
) -> CrossDocumentValidationResult:
    """
    Validate facts across original, simplified, and structured documents.

    Original text is always the source of truth.

    Args:
        original_text: Original document (source of truth)
        simplified_text: Simplified text from M5 (optional)
        structured_information: Structured information from M6 (optional)

    Returns:
        CrossDocumentValidationResult with validation details
    """
    start_time = time.time()

    # Extract critical facts from original (source of truth)
    original_facts = extract_critical_facts(original_text)

    preservation_details = []
    contradictions = []
    facts_preserved = 0
    facts_changed = 0
    facts_missing = 0

    # Validate each original fact against simplified and structured documents
    for fact in original_facts:
        # Map M5 fact_type to M7 FactType
        fact_type_m7 = map_fact_type_m5_to_m7(fact.fact_type)

        detail = FactPreservationDetail(
            fact_type=fact_type_m7,
            original_value=fact.value,
            preserved=False,
        )

        # Check simplified text
        simplified_has_fact = False
        if simplified_text:
            simplified_has_fact, simplified_value = check_fact_in_text(
                fact.fact_type, fact.value, simplified_text
            )
            detail.simplified_value = simplified_value

            if not simplified_has_fact:
                # Fact missing from simplified
                contradiction = FactContradiction(
                    fact_type=fact_type_m7,
                    original_value=fact.value,
                    simplified_value=None,
                    reason=f"{fact.fact_type.capitalize()} '{fact.value}' missing from simplified text",
                    severity="error",
                    original_location=fact.source_text,
                )
                contradictions.append(contradiction)
                facts_missing += 1
                preservation_details.append(detail)
                continue

        # Check structured information
        structured_has_fact = False
        structured_value = None
        if structured_information:
            structured_has_fact, structured_value = check_fact_in_structured(
                fact.fact_type, fact.value, structured_information
            )
            detail.structured_value = structured_value

            if not structured_has_fact and not simplified_text:
                # Fact missing from structured (and no simplified to check)
                contradiction = FactContradiction(
                    fact_type=fact_type_m7,
                    original_value=fact.value,
                    structured_value=None,
                    reason=f"{fact.fact_type.capitalize()} '{fact.value}' not found in structured information",
                    severity="error",
                    original_location=fact.source_text,
                )
                contradictions.append(contradiction)
                facts_missing += 1
                preservation_details.append(detail)
                continue

        # If we got here, fact is preserved in at least one document
        detail.preserved = True
        facts_preserved += 1
        preservation_details.append(detail)

    processing_time_ms = int((time.time() - start_time) * 1000)

    # Determine overall status
    validation_passed = len(contradictions) == 0
    overall_status = ValidationStatus.PASS if validation_passed else ValidationStatus.FAIL

    result = CrossDocumentValidationResult(
        validation_passed=validation_passed,
        overall_status=overall_status,
        facts_checked=len(original_facts),
        facts_preserved=facts_preserved,
        facts_changed=len([c for c in contradictions if c.severity == "error"]),
        facts_missing=facts_missing,
        contradictions=contradictions,
        preservation_details=preservation_details,
        processing_time_ms=processing_time_ms,
        metadata={
            "original_text_length": len(original_text),
            "simplified_text_length": len(simplified_text) if simplified_text else 0,
            "has_simplified": simplified_text is not None,
            "has_structured": structured_information is not None,
        },
    )

    return result


def check_fact_in_text(fact_type: str, fact_value: str, text: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a fact exists in text, accounting for format normalization.

    Args:
        fact_type: Type of fact (deadline, money, percentage, age, quantity)
        fact_value: Fact value from original
        text: Text to check in

    Returns:
        Tuple of (found: bool, found_value: Optional[str])
    """
    if fact_type == "deadline":
        return check_date_in_text(fact_value, text)
    elif fact_type == "money":
        return check_money_in_text(fact_value, text)
    elif fact_type == "percentage":
        return check_percentage_in_text(fact_value, text)
    elif fact_type == "age":
        return check_age_in_text(fact_value, text)
    elif fact_type == "quantity":
        return check_quantity_in_text(fact_value, text)
    else:
        # For other types, do exact or fuzzy match
        if fact_value in text:
            return True, fact_value
        # Try case-insensitive
        if fact_value.lower() in text.lower():
            return True, fact_value
        return False, None


def check_date_in_text(date_value: str, text: str) -> Tuple[bool, Optional[str]]:
    """Check if a date exists in text with format normalization."""
    # Normalize the original date
    normalized_original = normalize_date_format(date_value)

    # Try exact match first
    if date_value in text:
        return True, date_value

    # Extract all dates from text and normalize
    date_patterns = [
        r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{1,2}-\d{1,2}-\d{4})",  # DD-MM-YYYY
        r"(\d{1,2}/\d{1,2}/\d{4})",  # DD/MM/YYYY
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
    ]

    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            found_date_str = match.group(1) if match.lastindex else match.group(0)
            normalized_found = normalize_date_format(found_date_str)

            if normalized_original == normalized_found:
                return True, found_date_str

    return False, None


def check_money_in_text(money_value: str, text: str) -> Tuple[bool, Optional[str]]:
    """Check if a monetary amount exists in text with normalization."""
    # Extract numeric value from money_value
    numeric_match = re.search(r"(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)", money_value)
    if not numeric_match:
        return False, None

    numeric_value = numeric_match.group(1)
    normalized_value = numeric_value.replace(",", "")

    # Try exact match
    if money_value in text:
        return True, money_value

    # Try with different currency symbols
    currency_patterns = [
        rf"[₹]\s*{re.escape(numeric_value)}",
        rf"Rs\.\s*{re.escape(numeric_value)}",
        rf"INR\s+{re.escape(numeric_value)}",
        rf"[₹]\s*{normalized_value}",
        rf"Rs\.\s*{normalized_value}",
        rf"INR\s+{normalized_value}",
    ]

    for pattern in currency_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, numeric_value

    return False, None


def check_percentage_in_text(percentage_value: str, text: str) -> Tuple[bool, Optional[str]]:
    """Check if a percentage exists in text."""
    # Extract numeric value
    numeric_match = re.search(r"(\d+(?:\.\d+)?)", percentage_value)
    if not numeric_match:
        return False, None

    numeric_value = numeric_match.group(1)

    # Try exact match
    if percentage_value in text:
        return True, percentage_value

    # Try alternative formats
    patterns = [
        rf"{numeric_value}%",
        rf"{numeric_value}\s+percent",
        rf"{numeric_value}\s+per\s+cent",
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, numeric_value + "%"

    return False, None


def check_age_in_text(age_value: str, text: str) -> Tuple[bool, Optional[str]]:
    """Check if an age requirement exists in text."""
    # Extract numeric value
    numeric_match = re.search(r"(\d+)", age_value)
    if not numeric_match:
        return False, None

    numeric_value = numeric_match.group(1)

    # Try exact match
    if age_value in text:
        return True, age_value

    # Try alternative formats
    patterns = [
        rf"{numeric_value}\s+years",
        rf"{numeric_value}\s+year",
        rf"{numeric_value}\+",
        rf"at\s+least\s+{numeric_value}",
        rf"minimum\s+age\s+(?:is\s+)?{numeric_value}",
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"{numeric_value} years"

    return False, None


def check_quantity_in_text(quantity_value: str, text: str) -> Tuple[bool, Optional[str]]:
    """Check if a quantity exists in text."""
    # Extract numeric value
    numeric_match = re.search(r"(\d+(?:,\d{3})*(?:\.\d+)?)", quantity_value)
    if not numeric_match:
        return False, None

    numeric_value = numeric_match.group(1)
    normalized_value = numeric_value.replace(",", "")

    # Try exact match
    if quantity_value in text:
        return True, quantity_value

    # Try with different formatting
    if f"{numeric_value}" in text:
        return True, numeric_value
    if f"{normalized_value}" in text:
        return True, normalized_value

    return False, None


def check_fact_in_structured(
    fact_type: str, fact_value: str, structured_info: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Check if a fact exists in structured information.

    Args:
        fact_type: Type of fact
        fact_value: Fact value from original
        structured_info: Structured information dictionary

    Returns:
        Tuple of (found: bool, found_value: Optional[str])
    """
    # Map fact types to structured fields
    if fact_type == "deadline":
        deadlines = structured_info.get("deadlines", [])
        for deadline in deadlines:
            deadline_date = deadline.get("date")
            if deadline_date:
                normalized_original = normalize_date_format(fact_value)
                normalized_found = normalize_date_format(deadline_date)
                if normalized_original == normalized_found:
                    return True, deadline_date
        return False, None

    elif fact_type == "money":
        financial = structured_info.get("financial_information", [])
        for amount in financial:
            amount_value = amount.get("amount", "")
            if amount_value:
                # Extract numeric values
                original_numeric = re.sub(r"[^\d.,]", "", fact_value)
                found_numeric = re.sub(r"[^\d.,]", "", amount_value)
                # Normalize by removing commas
                if original_numeric.replace(",", "") == found_numeric.replace(",", ""):
                    return True, amount_value
        return False, None

    elif fact_type == "percentage":
        percentages = structured_info.get("percentages", [])
        for pct in percentages:
            pct_value = pct.get("percentage", "")
            if pct_value:
                # Extract numeric values
                original_numeric = re.search(r"(\d+(?:\.\d+)?)", fact_value)
                found_numeric = re.search(r"(\d+(?:\.\d+)?)", pct_value)
                if original_numeric and found_numeric:
                    if original_numeric.group(1) == found_numeric.group(1):
                        return True, pct_value
        return False, None

    elif fact_type == "age":
        ages = structured_info.get("age_requirements", [])
        for age_req in ages:
            min_age = age_req.get("minimum_age")
            if min_age:
                # Extract numeric from fact_value
                numeric_match = re.search(r"(\d+)", fact_value)
                if numeric_match and int(numeric_match.group(1)) == min_age:
                    return True, f"{min_age} years"
        return False, None

    elif fact_type == "quantity":
        # Check in required documents or other places
        required_docs = structured_info.get("required_documents", [])
        if required_docs:
            return True, str(len(required_docs))  # Simplified check
        return False, None

    else:
        return False, None


def log_validation_result(result: CrossDocumentValidationResult) -> None:
    """Log validation result details."""
    logger.info(
        f"Fact validation complete: "
        f"passed={result.validation_passed}, "
        f"facts_checked={result.facts_checked}, "
        f"preserved={result.facts_preserved}, "
        f"contradictions={len(result.contradictions)}"
    )

    if result.contradictions:
        for contradiction in result.contradictions:
            logger.warning(f"  Contradiction: {contradiction.fact_type.value} - {contradiction.reason}")
