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


# ============================================================
# Shared helpers
# ============================================================

# A standalone pagination marker such as "Page 5 of 7" is never a fact.
PAGE_MARKER_RE = re.compile(
    r"^\s*pages?\s+\d+(?:\s*(?:of|out\s+of|/)\s+\d+)?\s*\.?\s*$",
    re.IGNORECASE,
)

# Words that show a fragment is a clause rather than the name of a document.
CLAUSE_WORDS_RE = re.compile(
    r"\b(shall|must|will|should|would|may|might|can|could|is|are|was|were|be|been|"
    r"being|has|have|had|do|does|did|require|requires|required|need|needs|"
    r"applicant|applicants|student|students|institution|institutions|commission|"
    r"portal|government|authority)\b",
    re.IGNORECASE,
)

# Words that show a statement is an action somebody has to take.
ACTION_WORD_RE = re.compile(
    r"\b(shall|must|will|should|may|can|could|is|are|was|were|has|have|had|need|needs|"
    r"required|require|requires|apply|applies|applied|submit|submits|submitted|"
    r"upload|uploads|uploaded|send|sends|sent|provide|provides|provided|"
    r"furnish|furnishes|furnished|attach|attaches|attached|obtain|obtains|obtained|"
    r"collect|download|print|fill|write|verify|verifies|verified|ensure|ensures|"
    r"deposit|remit|register|pay|pays|paid|claim|generate|forward|transmit|"
    r"retain|retains|produce|produces|approach|contact|comply|eligible|entitled|"
    r"responsible|liable|reject|rejected|accept|accepted|complete|completing|"
    r"ask|asked|notified|remain|open|prohibited|permitted|included|including|"
    r"having|accredited|recognised|recognized|empowered|awarding|deemed|"
    r"specified|prescribed|constitute|belongs|importance|earmarked|registered|"
    r"relinquish|cancel|tender|avail|declared|short\s+listed)\b",
    re.IGNORECASE,
)

# A document name is short; a long span is a sentence, not a name.
MAX_DOCUMENT_NAME_LENGTH = 60

# Short words that end a sentence rather than abbreviate something.
_NOT_ABBREVIATIONS = {
    "the", "and", "but", "for", "nor", "are", "was", "were", "has", "have", "had",
    "its", "all", "you", "may", "can", "not", "his", "her", "she", "they", "them",
    "this", "that", "who", "how", "why", "now", "new", "old", "per", "via", "one",
    "two", "any", "our", "out", "off", "let", "set", "get", "far", "too", "see",
    "say", "use", "own", "due", "end", "ask", "aid", "add",
}
# Words that show a statement is a rule that does NOT apply.
NEGATION_MARKERS = (
    "not eligible",
    "ineligible",
    "are not",
    "is not",
    "shall not",
    "must not",
    "cannot",
    "can not",
    "no longer",
    "not permitted",
    "not allowed",
    "not to apply",
    "not available",
    "not be given",
    "not be considered",
    "not receive",
)

# Words that show a statement is about who qualifies.
ELIGIBILITY_KEYWORDS = (
    "eligible",
    "eligibility",
    "qualif",
    "must be a",
    "must be an",
    "must have",
    "shall have",
    "reside",
    "belong",
    "citizen",
    "income",
    "marks",
    "not be in receipt",
    "not in receipt of",
    "admitted",
    "enrolled",
    "pursuing",
    "seeking",
)


def _is_page_marker(text: str) -> bool:
    """True when the text is only a pagination marker."""
    return bool(PAGE_MARKER_RE.match(text.strip()))


def _is_heading(text: str) -> bool:
    """True when the text looks like a section heading rather than a statement."""
    letters = [char for char in text if char.isalpha()]
    if len(letters) < 3:
        return False
    return all(char.isupper() for char in letters)


def _is_heading_line(line: str) -> bool:
    """
    True when a line is a section heading.

    A numbered or lettered heading such as "1. ELIGIBILITY" or "IV. PROCEDURE"
    is a title, not a statement, and must not become a fact.
    """
    candidate = line.strip()
    candidate = re.sub(r"^\s*(\d{1,3}|[IVXLCDMivxlcdm]{1,6})[.)\s]\s*", "", candidate)
    candidate = re.sub(r"^\s*[-*•#]+\s*", "", candidate)
    candidate = candidate.strip()
    if len(candidate) < 3:
        return False
    letters = [char for char in candidate if char.isalpha()]
    if len(letters) < 3:
        return False
    if not all(char.isupper() for char in letters):
        return False
    return " " in candidate or len(letters) >= 4


# Short words that are abbreviations rather than the end of a sentence.
_ABBREVIATIONS = {
    "rs", "no", "art", "fig", "ref", "sec", "cl", "para", "m/s", "dr", "mr",
    "mrs", "ms", "prof", "st", "jr", "sr", "vol", "pp", "ed", "viz", "cf",
    "ie", "eg", "etc", "www", "http", "https", "pp", "vol", "ugc", "aishe",
    "govt", "dept", "m/s",
}


def _ends_sentence(text: str, index: int) -> bool:
    """
    True when the punctuation at ``index`` really ends a sentence.

    "Rs. 2,50,000" contains a full stop that does not end a sentence, and
    splitting on it would cut a rule in half. An abbreviation only counts as
    an abbreviation when the sentence continues after it, so "NSP." at the
    end of a sentence still ends it.
    """
    char = text[index]
    if char not in ".!?":
        return False
    if char != ".":
        return True

    # "www.ugc.ac.in" - a full stop inside a name, not the end of a sentence.
    following = text[index + 1: index + 2]
    if following.islower():
        return False

    start = index
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "'-/"):
        start -= 1
    word = text[start:index].lower().strip()

    if word in _ABBREVIATIONS:
        # The sentence continues when a lower case letter or a digit follows.
        following = text[index + 1:].lstrip()
        if following and (following[0].islower() or following[0].isdigit()):
            return False

    return True


def _clean_fragment(text: str) -> str:
    """Removes leading and trailing punctuation and list noise from a fragment."""
    cleaned = text.strip()
    cleaned = re.sub(r"^[\s,;:\-–—•*]+", "", cleaned)
    cleaned = re.sub(r"[\s,;:\-–—•*]+$", "", cleaned)
    # Drop a leading section heading such as "(iii) ONLY ONE BENEFIT:".
    cleaned = re.sub(
        r"^\(?[IVXLCDMivxlcdm0-9]{1,6}\)?\s+[A-Z][A-Z0-9 ,.'()/&:-]{2,}:\s*",
        "",
        cleaned,
    )
    # Drop a leading list marker such as "III." or "(i)" or "4)" that belongs
    # to the numbering of the source, not to the statement itself.
    cleaned = re.sub(r"^\(?[IVXLCDMivxlcdm0-9]{1,6}\)?[.)\s]+\s*", "", cleaned)
    # A statement that was wrapped over several lines reads as one line.
    cleaned = re.sub(r"\s*\n\s*", " ", cleaned)
    return cleaned.strip()


def _clean_list_item(text: str) -> str:
    """
    Cleans one item of a list.

    A list item may start with the conjunction that joined it to the previous
    item ("and bank account details"), which has to go. This is deliberately
    separate from :func:`_clean_fragment`, which must never remove the first
    word of a sentence.
    """
    cleaned = _clean_fragment(text)
    cleaned = re.sub(r"^(?:and|or)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _first_sentence(text: str) -> str:
    """Returns the first sentence of a piece of text."""
    match = re.search(r"[.!?](\s|$)", text)
    if match:
        return text[: match.end()].strip()
    return text.strip()


def _sentence_around(text: str, start: int, end: int) -> str:
    """
    Returns the sentence that contains the given span.

    Used to turn a matched keyword into a complete statement instead of a
    fragment that stops at the end of a line.
    """
    left = 0
    index = start - 1
    while index >= 0:
        char = text[index]
        if char in ".!?" and _ends_sentence(text, index):
            left = index + 1
            break
        if char == "\n":
            if index + 1 < len(text) and text[index + 1] in "\r\n":
                left = index + 1
                break
        index -= 1

    right = len(text)
    for match in re.finditer(r"[.!?]|\n[ \t]*\r?\n", text[end:]):
        if match.group(0).startswith("\n"):
            right = end + match.start()
            break
        if _ends_sentence(text, end + match.start()):
            right = end + match.start() + 1
            break

    return text[left:right].strip()


def strip_page_markers(text: str) -> str:
    """
    Removes standalone page markers such as "Page 3 of 7".

    A page marker is printing metadata, not content. It is removed as a whole
    line, so the sentences around it stay apart and a sentence that was split
    by a page break is put back together.
    """
    if not text:
        return text

    kept = [line for line in text.split("\n") if not _is_page_marker(line)]
    return "\n".join(kept)


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

    # Page markers are printing metadata. They are removed before anything is
    # extracted, so they can never end up inside a fact or split a sentence.
    text = strip_page_markers(text)

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
    # A page marker is printing metadata, never content.
    text = strip_page_markers(text)

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
    # A page marker is printing metadata, never content.
    text = strip_page_markers(text)

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
    """
    Extract age requirements, keeping the direction of the rule.

    "must be under 30 years" and "must be at least 30 years" are opposites,
    so the word that says which side of the number applies is captured as
    well and stored in ``qualifier``.
    """
    # A page marker is printing metadata, never content.
    text = strip_page_markers(text)

    requirements = []

    # ORDER MATTERS: the explicit directions are matched before the plain
    # "18 years old" form, so a rule is never read the wrong way round.
    # The direction word may be separated from the number by a filler such as
    # "the age of" ("below the age of 30 years").
    age_patterns = [
        (r'between\s+(?P<low>\d{1,3})\s+and\s+(?P<high>\d{1,3})\s+years?', 'range'),
        (r'(?P<low>\d{1,3})\s+to\s+(?P<high>\d{1,3})\s+years?', 'range'),
        # An upper bound: under, below, less than, not more than, at most.
        (r'(?P<qual>under|below|less\s+than|not\s+more\s+than|not\s+above|'
         r'not\s+exceeding|up\s+to|within|at\s+most|max(?:imum)?\s*(?:age\s*)?(?:of\s*)?)'
         r'\s*(?:the\s+)?(?:age\s+of\s*)?(?P<high>\d{1,3})\s+years?', 'upper'),
        # A lower bound: at least, not less than, minimum, above, over.
        (r'(?P<qual>at\s+least|not\s+less\s+than|no\s+less\s+than|'
         r'min(?:imum)?\s*(?:age\s*)?(?:of\s*)?|more\s+than\s+or\s+equal\s+to|'
         r'over|above|more\s+than|exceeding|at\s+minimum)'
         r'\s*(?:the\s+)?(?:age\s+of\s*)?(?P<low>\d{1,3})\s+years?', 'lower'),
        (r'(?P<low>\d{1,3})\s+years?\s+(?P<qual>or\s+older|or\s+above|or\s+more|and\s+above)', 'lower'),
        (r'(?P<high>\d{1,3})\s+years?\s+(?P<qual>or\s+younger|or\s+below|or\s+less|and\s+below)', 'upper'),
        (r'(?P<low>\d{1,3})\s+years?\s+(?:old|of\s+age)', 'lower'),
    ]

    seen = set()
    taken: List[Tuple[int, int]] = []

    for pattern, kind in age_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # A rule that was already read in a more specific form is skipped.
            if any(match.start() < end and match.end() > start for start, end in taken):
                continue

            groups = match.groupdict()
            low = groups.get('low')
            high = groups.get('high')
            qualifier = groups.get('qual')

            minimum_age = int(low) if low is not None else None
            maximum_age = int(high) if high is not None else None

            if kind == 'range' and minimum_age is not None and maximum_age is not None:
                # Make sure the smaller number is the lower bound.
                if maximum_age < minimum_age:
                    minimum_age, maximum_age = maximum_age, minimum_age
            elif kind == 'upper':
                minimum_age = None
            elif kind == 'lower':
                maximum_age = None

            if minimum_age is None and maximum_age is None:
                continue

            key = (minimum_age, maximum_age)

            if key not in seen:
                seen.add(key)
                taken.append((match.start(), match.end()))
                source_text = extract_surrounding_text(text, match.start(), match.end(), 50)
                requirements.append(ExtractedAgeRequirement(
                    minimum_age=minimum_age,
                    maximum_age=maximum_age,
                    qualifier=qualifier,
                    original_text=source_text
                ))

    return requirements


# A document name has to contain one of these. "Account", "bank" and
# "details" on their own are too weak: "the bank account must be Aadhaar
# linked" is a condition on the account, not a document to submit.
STRONG_DOCUMENT_WORDS = (
    "aadhaar",
    "pan card",
    "pan",
    "itr",
    "certificate",
    "letter",
    "proof",
    "card",
    "passport",
    "licence",
    "license",
    "form",
    "receipt",
    "marksheet",
    "mark sheet",
    "transcript",
    "diploma",
    "degree certificate",
    "bonafide",
    "undertaking",
    "account details",
    "bank statement",
    "affidavit",
    "caste certificate",
    "income certificate",
)


def _looks_like_a_document(item: str) -> bool:
    """True when the fragment names a document the applicant has to provide."""
    lowered = item.lower()
    return any(word in lowered for word in STRONG_DOCUMENT_WORDS)


def extract_required_documents(text: str) -> List[ExtractedDocument]:
    """Extract required documents."""
    # A page marker is printing metadata, never content.
    text = strip_page_markers(text)

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
                # "documents to the institution: Aadhaar card" - the list
                # starts after the colon.
                item = re.sub(r"^[^:]{0,60}:\s*", "", item)
                item = _clean_list_item(item)
                if len(item) < 2:
                    continue

                # A document name is a short noun phrase. A long span, or one
                # that contains a clause, is a sentence that merely mentions a
                # document and must not become a bullet of its own.
                if len(item) > MAX_DOCUMENT_NAME_LENGTH:
                    continue
                if CLAUSE_WORDS_RE.search(item):
                    continue
                # A fragment that ends in an infinitive ("... to enable") is
                # part of a sentence, not a name.
                if re.search(r"\bto\s+[a-z]+$", item, re.IGNORECASE):
                    continue
                # The name has to actually name a document.
                if not _looks_like_a_document(item):
                    continue
                if _is_page_marker(item) or _is_heading(item):
                    continue

                if item not in extracted_text:
                    extracted_text.add(item)
                    documents.append(ExtractedDocument(
                        name=item,
                        description=None,
                        original_text=item
                    ))

    # A document is only reported when the source actually asks for it. A bare
    # mention of a name - "the bank account must be Aadhaar linked" - is a
    # condition on the account, not a document to submit, so it is not turned
    # into a required document.

    return documents


def extract_monetary_amounts(text: str) -> List[ExtractedMonetaryAmount]:
    """Extract monetary amounts."""
    # A page marker is printing metadata, never content.
    text = strip_page_markers(text)

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

            # The clause the amount sits in says what the money is for.
            purpose = _clause_context(text, match.start(), match.end()) or None

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


def _clause_context(text: str, start: int, end: int) -> str:
    """
    The clause a percentage belongs to.

    A percentage on its own ("30%") says nothing. The clause it sits in - "30%
    slots will be reserved for the women candidates" - says what it is about.
    """
    left = start
    while left > 0:
        char = text[left - 1]
        if char in ".;,":
            break
        # A blank line ends the paragraph, a single line break is a wrap.
        if char == "\n" and text[left - 2: left] == "\n":
            break
        left -= 1

    right = end
    while right < len(text):
        char = text[right]
        if char in ".;":
            break
        if char == "\n" and text[right + 1: right + 2] == "\n":
            break
        right += 1

    # The clause ends at the next comma as well, so that a sentence with two
    # percentages gives each of them its own context.
    comma = text.find(",", end, right)
    if comma != -1:
        right = comma

    clause = text[left:right].strip()
    clause = re.sub(r"^[,;:]\s*", "", clause)
    # A discourse marker is not part of the fact.
    clause = re.sub(
        r"^(?:However|Further|Moreover|Also|Note|Thus|Therefore|Meanwhile)\b[,:]?\s*",
        "",
        clause,
        flags=re.IGNORECASE,
    )
    clause = re.sub(r"\s+", " ", clause)
    return clause.strip(" ,;:")


def extract_percentages(text: str) -> List[ExtractedPercentage]:
    """Extract percentage values together with what they are about."""
    # A page marker is printing metadata, never content.
    text = strip_page_markers(text)

    percentages = []

    percent_patterns = [
        r'(\d{1,3}(?:\.\d{1,2})?)%',
        r'(\d{1,3}(?:\.\d{1,2})?)\s+percent',
    ]

    seen = set()
    for pattern in percent_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            percent_str = match.group(1)
            context = _clause_context(text, match.start(), match.end())

            key = (percent_str, context.lower())
            if key in seen:
                continue
            seen.add(key)

            source_text = extract_surrounding_text(text, match.start(), match.end(), 80)

            percentages.append(ExtractedPercentage(
                percentage=f"{percent_str}%",
                value=float(percent_str),
                purpose=context or None,
                original_text=source_text
            ))

    return percentages


def extract_contact_information(text: str) -> List[ExtractedContactInfo]:
    """Extract contact information."""
    # A page marker is printing metadata, never content.
    text = strip_page_markers(text)

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
    # A page marker is printing metadata, never content.
    text = strip_page_markers(text)

    requirements = []

    # Patterns that introduce an eligibility statement. The matched span is
    # expanded to the surrounding sentence so the requirement is a complete
    # statement rather than a fragment that stops at the end of a line.
    eligibility_patterns = [
        r'(?:eligible|eligibility)[:\s]+',
        # A rule about the applicant. An age bound ("must be under 30 years")
        # is excluded here, because the age requirement already reports it.
        r'(?:candidates?|applicants?|students?)\s+'
        r'(?:must|should|shall)\s+'
        r'(?!be\s+(?:under|below|above|over|at\s+least|not\s+more|less\s+than|more\s+than)\b)',
    ]

    seen = set()

    for pattern in eligibility_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # A heading such as "1. ELIGIBILITY" introduces the section, it is
            # not a rule about the applicant. The first statement of the
            # section is the rule the section is about.
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.start())
            if line_end == -1:
                line_end = len(text)

            if _is_heading_line(text[line_start:line_end]):
                following = _first_sentence(text[match.end():].lstrip("\n"))
                sentence = following
            else:
                sentence = _sentence_around(text, match.start(), match.end())

            req = _clean_fragment(sentence)

            # A requirement has to be a statement, not a heading and not a
            # two-word fragment such as "KYC-compliant".
            if len(req) < 20 or len(req) > 300:
                continue
            if _is_page_marker(req) or _is_heading(req):
                continue
            if not ACTION_WORD_RE.search(req):
                continue
            # A rule about who qualifies, not a step of the procedure.
            if not any(keyword in req.lower() for keyword in ELIGIBILITY_KEYWORDS):
                continue

            if req not in seen:
                seen.add(req)
                # A rule that does not apply is labelled so it can never be
                # read as a positive requirement.
                lowered = req.lower()
                negated = any(marker in lowered for marker in NEGATION_MARKERS)
                requirements.append(ExtractedRequirement(
                    requirement=req,
                    category="Not eligible" if negated else None,
                    original_text=req
                ))

    # The numbered items of a section about who qualifies are eligibility
    # rules as well - the list of institutions, for example.
    headings = _section_headings(text)
    for match in re.finditer(
        r'^\s*(?:\d{1,2}|[IVXLCDMivxlcdm]{1,6})[.)\s:]\s+', text, re.MULTILINE
    ):
        if _heading_kind(headings, match.start()) != "eligibility":
            continue

        item = _first_sentence(_clean_fragment(_item_text(text, match.start())))
        if len(item) < 20 or len(item) > 300:
            continue
        if _is_page_marker(item) or _is_heading(item):
            continue
        # The section heading already says that these are rules, so an item
        # without a verb - "Institutions of National Importance." - is a rule
        # as well.
        if item in seen:
            continue

        seen.add(item)
        negated = any(marker in item.lower() for marker in NEGATION_MARKERS)
        requirements.append(ExtractedRequirement(
            requirement=item,
            category="Not eligible" if negated else None,
            original_text=item
        ))

    return requirements


# The start of the next numbered or lettered item.
_NEXT_ITEM_RE = re.compile(r"(?m)^\s*(?:\d{1,3}|[IVXLCDMivxlcdm]{1,6})[.)\s]\s")


def _item_text(text: str, start: int) -> str:
    """
    The text of a numbered item, from its marker to the next item.

    An item can hold several sentences ("... only. Students who have already
    acquired a postgraduate degree are not eligible to apply."), and all of
    them belong to the item.
    """
    rest = text[start:]

    blank = re.search(r"\n\s*\n", rest)
    limit = blank.start() if blank else len(rest)
    segment = rest[:limit]

    # The item ends where the next item starts. The first marker in the
    # segment belongs to this item, so the second one ends it.
    markers = list(_NEXT_ITEM_RE.finditer(segment))
    if len(markers) > 1:
        segment = segment[: markers[1].start()]

    return segment.strip()


# Words that mark a section as a procedure. The items under such a section
# are steps of the application.
PROCEDURE_HEADING_WORDS = (
    "procedure",
    "how to apply",
    "availing",
    "step",
    "process",
    "applying",
    "application procedure",
)

# Words that mark a section as a set of rules about who qualifies. The items
# under such a section are eligibility rules, not steps.
ELIGIBILITY_HEADING_WORDS = (
    "eligib",
    "type",
    "institution",
    "categor",
    "criteria",
    "who can apply",
    "beneficiar",
)


def _section_headings(text: str) -> List[Tuple[int, str]]:
    """
    The section headings of a text, with their position.

    A heading is a short line written in capitals and ending in a colon, for
    example "(i) ELIGIBILITY:" or "4. PROCEDURE FOR AVAILING THE SCHOLARSHIP:".
    """
    headings: List[Tuple[int, str]] = []
    offset = 0

    for line in text.split("\n"):
        candidate = line.strip()
        if candidate and ":" in candidate:
            head = candidate.split(":", 1)[0]
            # The marker of the section is not part of the title.
            head = re.sub(r"^\(?[IVXLCDMivxlcdm0-9]{1,6}\)?[.)\s]\s*", "", head).strip()
            if len(head) >= 3 and head == head.upper() and re.search(r"[A-Z]", head):
                headings.append((offset, head))
        offset += len(line) + 1

    return headings


def _heading_kind(headings: List[Tuple[int, str]], position: int) -> str:
    """Returns 'procedure', 'eligibility' or 'other' for the section at a position."""
    current = ""
    for start, title in headings:
        if start < position:
            current = title
        else:
            break

    lowered = current.lower()
    for word in PROCEDURE_HEADING_WORDS:
        if word in lowered:
            return "procedure"
    for word in ELIGIBILITY_HEADING_WORDS:
        if word in lowered:
            return "eligibility"
    return "other"


def extract_application_procedure(text: str) -> List[ExtractedProcedure]:
    """Extract application procedure steps."""
    # A page marker is printing metadata, never content.
    text = strip_page_markers(text)

    procedures = []

    # Numbered items using Arabic or Roman numerals, e.g. "1." or "IV.".
    # Government notices use both, and a Roman numeral clause is a real step.
    step_patterns = [
        r'(?:step|step\s+\d+)[:\s]*(\d+)[.:]?\s+',
        r'^\s*(\d{1,2}|[IVXLCDMivxlcdm]{1,6})[.)\s:]\s+',
    ]

    seen = set()
    step_num = 1
    headings = _section_headings(text)

    for pattern in step_patterns:
        for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
            # The items of a section about who qualifies are eligibility rules,
            # not steps of the application.
            if _heading_kind(headings, match.start()) == "eligibility":
                continue

            # The step is the whole item. A clause that was wrapped over
            # several lines, or that was split by a page break, is put back
            # together. The item marker is removed first, so that a roman
            # numeral such as "I." is not read as the end of a sentence.
            step_text = _first_sentence(_clean_fragment(_item_text(text, match.start())))

            # A section heading is not a step. "PROCEDURE FOR AVAILING THE
            # SCHOLARSHIP" is a title and must not become a bullet.
            if len(step_text) < 15 or len(step_text) > 300:
                continue
            if _is_page_marker(step_text) or _is_heading(step_text):
                continue
            if _is_heading_line(step_text):
                continue
            if not ACTION_WORD_RE.search(step_text):
                continue

            if step_text not in seen:
                seen.add(step_text)
                procedures.append(ExtractedProcedure(
                    step_number=step_num,
                    description=step_text,
                    original_text=step_text
                ))
                step_num += 1

    return procedures


def extract_important_conditions(text: str) -> List[ExtractedCondition]:
    """Extract important conditions and exceptions."""
    # A page marker is printing metadata, never content.
    text = strip_page_markers(text)

    conditions = []

    # Patterns that introduce a condition. The matched span is expanded to the
    # surrounding sentence so the condition is a complete statement.
    condition_patterns = [
        r'(?:Note|Important)\s*[:\-]\s*',
        r'(?:However|But|Exception|Except|Provided|Condition)\s*[:\-]?\s*',
        r'(?:shall\s+not|must\s+not|cannot|not\s+required\s+to|not\s+permitted\s+to|'
        r'not\s+entitled\s+to)\s+',
        r'(?:in\s+case\s+of|in\s+case,|in\s+the\s+event\s+of)\s+',
        # An obligation for one of the parties, for example "Students must
        # apply" or "Institutions must verify". It keeps the instruction for
        # applicants and the instruction for institutions apart.
        r'(?:students?|applicants?|candidates?|institutions?|parents?|scholarships?|'
        r'selection|results?|slots?|institution|university|college|authorities|'
        r'commission|nodal\s+officers?|list|centres?)\s+(?:\w+[\s,]+){0,4}?'
        r'(?:must|shall|should|can|have\s+to|has\s+to|are\s+required\s+to|'
        r'is\s+required\s+to|are\s+earmarked|is\s+earmarked)\s+',
        # An obligation without a named subject.
        r'(?:are|is)\s+required\s+to\s+be\s+',
        r'(?:shall|must)\s+have\s+to\s+',
    ]

    seen = set()

    for pattern in condition_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            cond = _clean_fragment(_sentence_around(text, match.start(), match.end()))
            # The label already says this is a condition, so the marker in the
            # source does not need to be repeated.
            cond = re.sub(
                r"^(?:Note|Important|However|But|Except)\s*[,:]?\s*",
                "",
                cond,
                flags=re.IGNORECASE,
            ).strip()

            if len(cond) < 20 or len(cond) > 400:
                continue
            if _is_page_marker(cond) or _is_heading(cond):
                continue
            if not ACTION_WORD_RE.search(cond):
                continue

            if cond not in seen:
                seen.add(cond)
                conditions.append(ExtractedCondition(
                    condition=cond,
                    type='note',
                    original_text=cond
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
