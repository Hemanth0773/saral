"""
Structured information extraction service.
Extracts structured information from government documents for cognitive accessibility.
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.schemas.extraction import (
    StructuredInformation,
    ExtractedDeadline,
    ExtractedDate,
    ExtractedRequirement,
    ExtractedAgeRequirement,
    ExtractedDocument,
    ExtractedMonetaryAmount,
    ExtractedPercentage,
    ExtractedProcedure,
    ExtractedCondition,
    ExtractedContactInfo,
    ExtractedLocation,
    ExtractedOrganization,
)
from app.services.validation_service import normalize_date_format
from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_structured_information(text: str, extract_title: bool = True, extract_summary: bool = True) -> StructuredInformation:
    """
    Extract structured information from text.

    Args:
        text: Source text to extract from
        extract_title: Whether to extract document title
        extract_summary: Whether to generate summary

    Returns:
        StructuredInformation object
    """
    structured_info = StructuredInformation()

    # Extract deadlines
    structured_info.deadlines = extract_deadlines(text)

    # Extract important dates
    structured_info.important_dates = extract_important_dates(text)

    # Extract age requirements
    structured_info.age_requirements = extract_age_requirements(text)

    # Extract required documents
    structured_info.required_documents = extract_required_documents(text)

    # Extract monetary amounts
    structured_info.financial_information = extract_monetary_amounts(text)

    # Extract percentages
    structured_info.percentages = extract_percentages(text)

    # Extract contact information
    structured_info.contact_information = extract_contact_information(text)

    # Extract locations
    structured_info.locations = extract_locations(text)

    # Extract organizations (entities)
    structured_info.organizations = extract_organizations(text)

    # Extract eligibility requirements (may use LLM or pattern-based)
    structured_info.eligibility_requirements = extract_eligibility_requirements(text)

    # Extract application procedure
    structured_info.application_procedure = extract_application_procedure(text)

    # Extract important conditions
    structured_info.important_conditions = extract_important_conditions(text)

    # Extract title if requested
    if extract_title:
        structured_info.title = extract_title_from_text(text)

    # Extract summary if requested
    if extract_summary:
        structured_info.summary = extract_summary_from_text(text)

    return structured_info


def extract_deadlines(text: str) -> List[ExtractedDeadline]:
    """Extract application deadlines from text."""
    deadlines = []

    # Patterns for deadlines with explicit "deadline" or "before" language
    deadline_patterns = [
        # Pattern: "deadline: 31 December 2026"
        (r'deadline\s*[:=]?\s*(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', 1),
        # Pattern: "Submit by December 31, 2026" (MDY format)
        (r'(?:by|submit\s+by|before|submit\s+before)\s+(?:the\s+)?((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})', 1),
        # Pattern: "before 31 December 2026" (DMY format)
        (r'(?:before|submit\s+before|by|submit\s+by)\s+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', 1),
        # Pattern: "on 31 December 2026" or "until 31 December 2026"
        (r'(?:on|until)\s+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', 1),
        # ISO format
        (r'(?:by|before|until)\s+(\d{4}-\d{2}-\d{2})', 1),
    ]

    seen = set()
    for pattern, group_idx in deadline_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Get the matched date string from the specified group
            date_str = match.group(group_idx)

            # Normalize date
            normalized_date = normalize_date_format(date_str)

            # Avoid duplicates
            if normalized_date in seen:
                continue
            seen.add(normalized_date)

            source_text = extract_surrounding_text(text, match.start(), match.end(), 50)

            deadlines.append(ExtractedDeadline(
                date=normalized_date,
                description="Application deadline",
                original_text=source_text
            ))

    return deadlines


def extract_important_dates(text: str) -> List[ExtractedDate]:
    """Extract important dates other than deadlines."""
    dates = []

    # Patterns for important dates (excluding deadline patterns)
    date_patterns = [
        r'(?:from|starting|begin|start|commence)\s+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
        r'(?:on|effective|valid\s+from)\s+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
        r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})(?:\s+to\s+)',
    ]

    seen = set()
    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            date_str = match.group(1)
            normalized_date = normalize_date_format(date_str)

            # Avoid duplicates and deadline overlap
            if normalized_date in seen:
                continue
            seen.add(normalized_date)

            source_text = extract_surrounding_text(text, match.start(), match.end(), 50)

            dates.append(ExtractedDate(
                date=normalized_date,
                description=None,
                original_text=source_text
            ))

    return dates


def extract_age_requirements(text: str) -> List[ExtractedAgeRequirement]:
    """Extract age requirements."""
    requirements = []

    # Patterns for age requirements - ORDER MATTERS! Check ranges first
    age_patterns = [
        # Range patterns (check these first to avoid matching individual numbers)
        (r'between\s+(\d{1,3})\s+and\s+(\d{1,3})\s+years?', 1, 2),
        (r'(\d{1,3})\s+to\s+(\d{1,3})\s+years?', 1, 2),
        # Single age patterns
        (r'(?:must\s+be\s+)?(?:at\s+least\s+|minimum\s+age\s+(?:is\s+)?)?(\d{1,3})\s+years?\s+(?:old|of\s+age)', 1, None),
    ]

    seen = set()
    for pattern_info in age_patterns:
        pattern = pattern_info[0]
        min_idx = pattern_info[1]
        max_idx = pattern_info[2]

        for match in re.finditer(pattern, text, re.IGNORECASE):
            source_text = extract_surrounding_text(text, match.start(), match.end(), 50)

            min_age = int(match.group(min_idx))
            max_age = int(match.group(max_idx)) if max_idx else None

            # Ensure min_age is truly the minimum when we have a range
            if max_age is not None and min_age > max_age:
                min_age, max_age = max_age, min_age

            key = (min_age, max_age)

            if key not in seen:
                seen.add(key)
                requirements.append(ExtractedAgeRequirement(
                    minimum_age=min_age,
                    maximum_age=max_age,
                    original_text=source_text
                ))

    return requirements


def extract_required_documents(text: str) -> List[ExtractedDocument]:
    """Extract required documents."""
    documents = []

    # Common document patterns
    doc_patterns = [
        r'(?:submit|provide|attach|furnish|need|require|must\s+submit)\s+(?:the\s+)?(?:following\s+)?(?:documents|papers|copies)?[:\s]*([^.!?\n]+(?:Aadhaar|PAN|ITR|certificate|letter|proof|card|account|bank|passport|license|ID|form|document|receipt|details)[^.!?\n]+)',
        r'(?:documents?\s+(?:required|needed|to\s+be\s+submitted))[:\s]*([^.!?\n]+)',
        r'-\s*([^.!?\n]*(?:Aadhaar|PAN|ITR|certificate|letter|proof|card|account|bank|passport|license|ID|form|receipt)[^.!?\n]*)',
        r'•\s*([^.!?\n]*(?:Aadhaar|PAN|ITR|certificate|letter|proof|card|account|bank|passport|license|ID|form|receipt)[^.!?\n]*)',
    ]

    extracted_text = set()

    for pattern in doc_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            match_text = match.group(1).strip()

            # Split by common separators to get individual documents
            doc_items = re.split(r'[,;]\s+', match_text)

            for item in doc_items:
                item = item.strip()
                if not item or len(item) < 2:
                    continue

                # Remove trailing punctuation
                item = re.sub(r'[,;.!?]+$', '', item).strip()

                if item not in extracted_text:
                    extracted_text.add(item)
                    documents.append(ExtractedDocument(
                        name=item,
                        description=None,
                        original_text=item
                    ))

    # Also look for common document names in bullet points or lists
    doc_names = [
        'Aadhaar', 'PAN card', 'ITR', 'income certificate', 'bank account details',
        'passport', 'driver\'s license', 'voter ID', 'birth certificate',
        'residence certificate', 'caste certificate', 'ration card',
    ]

    for doc in doc_names:
        if doc.lower() in text.lower() and doc not in extracted_text:
            match = re.search(re.escape(doc), text, re.IGNORECASE)
            if match:
                extracted_text.add(doc)
                source_text = extract_surrounding_text(text, match.start(), match.end(), 40)
                documents.append(ExtractedDocument(
                    name=doc,
                    description=None,
                    original_text=source_text
                ))

    return documents


def extract_monetary_amounts(text: str) -> List[ExtractedMonetaryAmount]:
    """Extract monetary amounts."""
    amounts = []

    # Patterns for Indian currency
    currency_patterns = [
        r'[₹]\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)',
        r'Rs\.\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)',
        r'INR\s+(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)',
    ]

    seen = set()
    for pattern in currency_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            amount_str = match.group(1)

            # Get the currency symbol
            currency = text[match.start()] if text[match.start()] in '₹' else '₹'

            # Avoid duplicates
            if amount_str in seen:
                continue
            seen.add(amount_str)

            source_text = extract_surrounding_text(text, match.start(), match.end(), 60)

            # Determine purpose from context
            purpose = None
            if 'assistance' in source_text.lower():
                purpose = 'assistance'
            elif 'fee' in source_text.lower():
                purpose = 'fee'
            elif 'interest' in source_text.lower():
                purpose = 'interest'
            elif 'loan' in source_text.lower():
                purpose = 'loan'
            elif 'scholarship' in source_text.lower():
                purpose = 'scholarship'

            # Normalize amount (remove commas, keep decimal)
            normalized = amount_str.replace(',', '')

            amounts.append(ExtractedMonetaryAmount(
                amount=f"{currency}{amount_str}",
                amount_normalized=normalized,
                currency=currency,
                purpose=purpose,
                original_text=source_text
            ))

    return amounts


def extract_percentages(text: str) -> List[ExtractedPercentage]:
    """Extract percentage values."""
    percentages = []

    percent_patterns = [
        r'(\d{1,3}(?:\.\d{1,2})?)%',
        r'(\d{1,3}(?:\.\d{1,2})?)\s+percent',
    ]

    seen = set()
    for pattern in percent_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            percent_str = match.group(1)

            if percent_str in seen:
                continue
            seen.add(percent_str)

            value = float(percent_str)
            source_text = extract_surrounding_text(text, match.start(), match.end(), 50)

            # Determine purpose
            purpose = None
            if 'interest' in source_text.lower():
                purpose = 'interest rate'
            elif 'discount' in source_text.lower():
                purpose = 'discount'
            elif 'tax' in source_text.lower():
                purpose = 'tax'

            percentages.append(ExtractedPercentage(
                percentage=f"{percent_str}%",
                value=value,
                purpose=purpose,
                original_text=source_text
            ))

    return percentages


def extract_contact_information(text: str) -> List[ExtractedContactInfo]:
    """Extract contact information."""
    contacts = []

    # Phone number patterns
    phone_patterns = [
        r'(?:phone|contact|call|telephone)[:\s]*(?:\+?91[-.\s]?)?(\d{4}[-.\s]?\d{4}[-.\s]?\d{4}|\d{10})',
        r'(\d{10})\s*(?:or\s+\d{10})*',  # Indian 10-digit numbers
    ]

    # Email patterns
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'

    # Address patterns
    address_patterns = [
        r'(?:address|office|located\s+at)[:\s]*([^.!?\n]+)',
    ]

    seen = set()

    # Extract phone numbers
    for pattern in phone_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            phone = match.group(1)
            if phone not in seen:
                seen.add(phone)
                source_text = extract_surrounding_text(text, match.start(), match.end(), 40)
                contacts.append(ExtractedContactInfo(
                    type='phone',
                    value=phone,
                    original_text=source_text
                ))

    # Extract emails
    for match in re.finditer(email_pattern, text):
        email = match.group(0)
        if email not in seen:
            seen.add(email)
            source_text = extract_surrounding_text(text, match.start(), match.end(), 40)
            contacts.append(ExtractedContactInfo(
                type='email',
                value=email,
                original_text=source_text
            ))

    # Extract addresses
    for pattern in address_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            address = match.group(1).strip()
            if address not in seen and len(address) > 5:
                seen.add(address)
                source_text = extract_surrounding_text(text, match.start(), match.end(), 50)
                contacts.append(ExtractedContactInfo(
                    type='address',
                    value=address,
                    original_text=source_text
                ))

    return contacts


def extract_locations(text: str) -> List[ExtractedLocation]:
    """Extract geographic locations and offices."""
    locations = []

    # Patterns for locations
    location_patterns = [
        r'(?:office|regional|branch|headquarters|center|centre)\s+(?:at|in|located\s+in)[:\s]*([^.!?,\n]+)',
        r'(?:available|available at)\s+(?:at|in)[:\s]*([^.!?,\n]+)',
    ]

    # Common Indian locations
    indian_locations = [
        'New Delhi', 'Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad',
        'Pune', 'Ahmedabad', 'Lucknow', 'Indore', 'Chandigarh', 'Jaipur',
    ]

    seen = set()

    # Extract from patterns
    for pattern in location_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            location = match.group(1).strip()
            if location not in seen and len(location) > 2:
                seen.add(location)
                source_text = extract_surrounding_text(text, match.start(), match.end(), 50)
                locations.append(ExtractedLocation(
                    location=location,
                    type='office',
                    original_text=source_text
                ))

    # Extract known locations if mentioned
    for loc in indian_locations:
        if loc.lower() in text.lower():
            match = re.search(re.escape(loc), text, re.IGNORECASE)
            if match and loc not in seen:
                seen.add(loc)
                source_text = extract_surrounding_text(text, match.start(), match.end(), 40)
                locations.append(ExtractedLocation(
                    location=loc,
                    type=None,
                    original_text=source_text
                ))

    return locations


def extract_organizations(text: str) -> List[ExtractedOrganization]:
    """Extract organizations and entities mentioned."""
    organizations = []

    # Patterns for organizations
    org_patterns = [
        r'(?:under|administered\s+by|implemented\s+by)[:\s]*([^.!?,\n]+)',
        r'(?:Government\s+of\s+[^.!?,\n]+)',
        r'([A-Z][A-Za-z\s]+(?:Ministry|Department|Bureau|Authority|Agency|Commission|Board))',
    ]

    # Known organizations
    known_orgs = [
        'Government of India',
        'Ministry of Housing and Urban Affairs',
        'Ministry of Labour',
        'NRLM',
        'PMAY',
    ]

    seen = set()

    # Extract from patterns
    for pattern in org_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            org = match.group(1 if match.lastindex else 0).strip()
            if org not in seen and len(org) > 3 and len(org) < 100:
                seen.add(org)
                source_text = extract_surrounding_text(text, match.start(), match.end(), 50)
                organizations.append(ExtractedOrganization(
                    name=org,
                    role=None,
                    original_text=source_text
                ))

    # Add known organizations if found
    for org in known_orgs:
        if org.lower() in text.lower() and org not in seen:
            match = re.search(re.escape(org), text, re.IGNORECASE)
            if match:
                seen.add(org)
                source_text = extract_surrounding_text(text, match.start(), match.end(), 50)
                organizations.append(ExtractedOrganization(
                    name=org,
                    role=None,
                    original_text=source_text
                ))

    return organizations


def extract_eligibility_requirements(text: str) -> List[ExtractedRequirement]:
    """Extract eligibility requirements."""
    requirements = []

    # Patterns for eligibility
    eligibility_patterns = [
        r'(?:eligible|eligibility)[:\s]+([^.!?\n]+)',
        r'(?:must|should)\s+(?:be|have)\s+([^.!?\n]+)',
        r'(?:candidates?|applicants?)\s+(?:must|should)\s+([^.!?\n]+)',
    ]

    seen = set()

    for pattern in eligibility_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            req = match.group(1).strip()

            # Filter out very short or very long matches
            if len(req) < 5 or len(req) > 200:
                continue

            if req not in seen:
                seen.add(req)
                source_text = extract_surrounding_text(text, match.start(), match.end(), 60)
                requirements.append(ExtractedRequirement(
                    requirement=req,
                    category=None,
                    original_text=source_text
                ))

    return requirements


def extract_application_procedure(text: str) -> List[ExtractedProcedure]:
    """Extract application procedure steps."""
    procedures = []

    # Look for numbered steps or bullet points
    step_patterns = [
        r'(?:step|step\s+\d+)[:\s]*(\d+)[.:]?\s+([^.!?\n]+)',
        r'^(\d+)[.)\s:]\s+([^.!?\n]+)',  # Numbered list
    ]

    seen = set()
    step_num = 1

    for pattern in step_patterns:
        for match in re.finditer(pattern, text, re.MULTILINE):
            if match.lastindex == 2:
                step_text = match.group(2).strip()
            else:
                step_text = match.group(1).strip()

            if len(step_text) > 5 and step_text not in seen:
                seen.add(step_text)
                source_text = extract_surrounding_text(text, match.start(), match.end(), 50)
                procedures.append(ExtractedProcedure(
                    step_number=step_num,
                    description=step_text,
                    original_text=source_text
                ))
                step_num += 1

    return procedures


def extract_important_conditions(text: str) -> List[ExtractedCondition]:
    """Extract important conditions and exceptions."""
    conditions = []

    # Patterns for conditions
    condition_patterns = [
        r'(?:Note|Important|Note:|Important:)[:\s]*([^.!?\n]+[.!?])',
        r'(?:However|But|Exception|Provided|Condition)[:\s]*([^.!?\n]+)',
        r'(?:shall\s+not|must\s+not|cannot)\s+([^.!?\n]+)',
    ]

    seen = set()

    for pattern in condition_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            cond = match.group(1).strip()
            if len(cond) > 5 and cond not in seen:
                seen.add(cond)
                source_text = extract_surrounding_text(text, match.start(), match.end(), 60)
                conditions.append(ExtractedCondition(
                    condition=cond,
                    type='note',
                    original_text=source_text
                ))

    return conditions


def extract_title_from_text(text: str) -> Optional[str]:
    """Extract document title from text."""
    # Look for title patterns
    title_patterns = [
        r'^[A-Z][A-Za-z\s]{5,50}(?:Scheme|Program|Policy|Guidelines|Rules)',
        r'(?:Title|Subject|Scheme|Program):\s*([^.!?\n]+)',
    ]

    for pattern in title_patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            title = match.group(1) if match.lastindex else match.group(0)
            return title.strip()

    # If no title found, return None
    return None


def extract_summary_from_text(text: str) -> Optional[str]:
    """Generate a brief summary from the first 100-150 characters."""
    # Extract first complete sentence
    sentences = re.split(r'[.!?]+', text)
    if sentences:
        first_sentence = sentences[0].strip()
        if len(first_sentence) > 10:
            return first_sentence
    return None


def extract_surrounding_text(text: str, start: int, end: int, context_chars: int = 50) -> str:
    """Extract text around a given position for context."""
    context_start = max(0, start - context_chars)
    context_end = min(len(text), end + context_chars)

    result = text[context_start:context_end]

    # Clean up if we cut in middle of a word
    if context_start > 0 and text[context_start].isalnum():
        while context_start > 0 and text[context_start - 1].isalnum():
            context_start -= 1
        result = text[context_start:context_end]

    if context_end < len(text) and text[context_end - 1].isalnum():
        while context_end < len(text) and text[context_end].isalnum():
            context_end += 1
        result = text[context_start:context_end]

    return result.strip()


def validate_critical_facts(structured_info: StructuredInformation, original_text: str) -> Dict[str, Any]:
    """
    Validate that critical facts are preserved and present.

    Args:
        structured_info: Extracted structured information
        original_text: Original text

    Returns:
        Dictionary with validation results
    """
    results = {
        "facts_extracted": False,
        "critical_facts_count": 0,
        "issues": []
    }

    fact_count = (
        len(structured_info.deadlines) +
        len(structured_info.important_dates) +
        len(structured_info.age_requirements) +
        len(structured_info.required_documents) +
        len(structured_info.financial_information) +
        len(structured_info.contact_information)
    )

    results["critical_facts_count"] = fact_count
    results["facts_extracted"] = fact_count > 0

    # Check if critical information is missing when expected
    if 'apply' in original_text.lower() or 'submit' in original_text.lower():
        if not structured_info.deadlines:
            results["issues"].append("Expected deadline information not found")

    if '₹' in original_text or 'rupees' in original_text.lower():
        if not structured_info.financial_information:
            results["issues"].append("Expected monetary information not found")

    return results
