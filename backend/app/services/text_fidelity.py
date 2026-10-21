"""
Text fidelity checks for simplified government documents.

The fact preservation check in :mod:`app.services.validation_service` is
one-directional: it verifies that dates, amounts, percentages, ages and
quantities from the source are still present in the simplified text. It does
not notice the opposite problem - the simplified text adding a claim that the
source never made.

This module covers the additions:

* pagination artifacts ("Page 4 of 7", "--- Page 3 (text) ---") that a model
  can turn into an application instruction,
* certainty that was upgraded ("normally announced" -> "will be announced"),
* entity types that were swapped ("university/college/institute" -> "school"),
* obligations that quote a number the source never states.

Every check is a plain function over two strings so it can be unit tested
without a model.
"""

import re
from typing import Dict, List, Optional, Sequence, Set, Tuple

# "Page 4", "Page 4 of 7", "pages 2-3"
PAGE_REFERENCE_RE = re.compile(
    r"\bpages?\s+\d+(?:\s*(?:of|out\s+of|/)\s*\d+)?\b", re.IGNORECASE
)

# A line that contains nothing but a page reference: "Page 4 of 7".
STANDALONE_PAGE_RE = re.compile(
    r"^[\s\-–—•*#]*pages?\s+\d+(?:\s*(?:of|out\s+of|/)\s*\d+)?\s*\.?$",
    re.IGNORECASE,
)

# The marker this backend adds between extracted pages.
BACKEND_PAGE_MARKER_RE = re.compile(
    r"^[\s\-–—•*#]*pages?\s+\d+\s*\((?:text|ocr|scanned|image|pdf|unknown)\)\s*[\s\-–—•*]*$",
    re.IGNORECASE,
)

# A page reference followed by a rule, e.g. "Page 4 ----" or "Page 4 ***".
DECORATED_PAGE_RE = re.compile(
    r"^[\s\-–—•*#]*pages?\s+\d+\s*[\-–—•*]{2,}\s*$", re.IGNORECASE
)

# Extraction artifacts that are not page references but carry no meaning.
OTHER_ARTIFACTS = {
    "--- SCANNED PAGES (OCR) ---",
    "[Image content - No OCR available]",
    "[Some scanned pages could not be read. Please install Tesseract OCR.]",
}

# Words that turn a statement into an instruction.
OBLIGATION_RE = re.compile(
    r"\b(must|shall|should|need\s+to|needs\s+to|required\s+to|has\s+to|have\s+to|"
    r"mandatory|compulsory|obliged\s+to)\b",
    re.IGNORECASE,
)

# Verbs that turn a fact into an action the reader has to perform.
INSTRUCTION_VERB_RE = re.compile(
    r"\b(declare|fill|write|attach|submit|upload|apply|send|submit\s+it|"
    r"mark|tick|sign|paste|enter|complete|obtain|collect)\b",
    re.IGNORECASE,
)

# Words that express a frequency or an expectation rather than a certainty.
FREQUENCY_HEDGES: Tuple[str, ...] = (
    "normally",
    "usually",
    "generally",
    "ordinarily",
    "typically",
    "in principle",
    "in most cases",
    "as far as possible",
    "where possible",
    "to the extent possible",
    "expected to",
    "likely",
    "approximately",
    "roughly",
)

# Phrases that attach a condition or an exception to a rule.
CONDITION_PHRASES: Tuple[str, ...] = (
    "subject to",
    "subject to the condition",
    "provided that",
    "conditional upon",
    "at the discretion of",
    "only if",
    "except",
    "unless",
    "in the event",
    "as a condition",
    "as long as",
)

# Any conditional construction counts as preserving the condition. A
# simplification that writes "subject to the condition that it is declared"
# as "if you already have one, you must declare it" has kept the meaning and
# must not be reported.
CONDITION_CONSTRUCTION_RE = re.compile(
    r"\b(subject to|provided that|conditional upon|at the discretion of|only if|"
    r"except|unless|in the event|as a condition|as long as|if)\b",
    re.IGNORECASE,
)

# Words that make a statement definite.
CERTAINTY_MARKERS: Tuple[str, ...] = (
    "will",
    "always",
    "definitely",
    "guaranteed",
    "certainly",
    "assured",
    "without fail",
    "shall",
    "must",
)

# Families of terms that must not be swapped for one another.
ENTITY_FAMILIES: Tuple[Tuple[str, ...], ...] = (
    (
        "university", "universities",
        "college", "colleges",
        "institute", "institutes",
        "institution", "institutions",
        "school", "schools",
        "polytechnic", "polytechnics",
        "academy", "academies",
    ),
    (
        "ministry", "ministries",
        "commission", "commissions",
        "board", "boards",
        "authority", "authorities",
        "tribunal", "tribunals",
        "court", "courts",
        "secretariat", "secretariats",
        "directorate", "directorates",
    ),
)

NUMBER_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


# ---------------------------------------------------------------------
# Document artifacts
# ---------------------------------------------------------------------

def _is_artifact_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped in OTHER_ARTIFACTS:
        return True
    return bool(
        STANDALONE_PAGE_RE.match(stripped)
        or BACKEND_PAGE_MARKER_RE.match(stripped)
        or DECORATED_PAGE_RE.match(stripped)
    )


def strip_document_artifacts(text: str) -> Tuple[str, List[str]]:
    """
    Removes pagination and extraction artifacts from a document.

    Args:
        text: Raw extracted document text

    Returns:
        Tuple of (cleaned text, list of removed artifact lines)
    """
    if not text:
        return "", []

    artifacts: List[str] = []
    kept: List[str] = []

    for line in text.split("\n"):
        if _is_artifact_line(line):
            artifacts.append(line.strip())
            continue
        kept.append(line)

    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return cleaned, artifacts


# ---------------------------------------------------------------------
# Page references
# ---------------------------------------------------------------------

def extract_page_references(text: str) -> List[str]:
    """Returns every page reference found in the text, in order."""
    if not text:
        return []
    return [match.group(0).strip() for match in PAGE_REFERENCE_RE.finditer(text)]


def _normalise_reference(reference: str) -> str:
    return re.sub(r"\s+", " ", reference.strip().lower())


def _split_sentences(text: str) -> List[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def _reference_is_in_instruction_context(text: str, reference: str) -> bool:
    """True when the reference appears in a sentence that reads as an instruction."""
    target = _normalise_reference(reference)
    for sentence in _split_sentences(text):
        if target not in _normalise_reference(sentence):
            continue
        if OBLIGATION_RE.search(sentence) or INSTRUCTION_VERB_RE.search(sentence):
            return True
    return False


def detect_page_reference_issues(original_text: str, simplified_text: str) -> List[str]:
    """
    Detects page numbers that were turned into content or instructions.

    A page reference is a document artifact, not a requirement. A model that
    reads "Page 4 of 7" in a footer and writes "you must declare on Page 4 of
    7 of your application" has invented an instruction.
    """
    issues: List[str] = []
    if not original_text or not simplified_text:
        return issues

    original_body, artifacts = strip_document_artifacts(original_text)

    artifact_refs: Set[str] = set()
    for artifact in artifacts:
        for reference in extract_page_references(artifact):
            artifact_refs.add(_normalise_reference(reference))

    body_refs = {
        _normalise_reference(reference)
        for reference in extract_page_references(original_body)
    }

    for reference in extract_page_references(simplified_text):
        key = _normalise_reference(reference)
        if key in body_refs:
            # The source really does mention this page, so repeating it is
            # only a problem when it became an instruction.
            if (
                not _reference_is_in_instruction_context(original_body, reference)
                and _reference_is_in_instruction_context(simplified_text, reference)
            ):
                issues.append(
                    f"Page reference '{reference}' was turned into an instruction the source does not state"
                )
        elif key in artifact_refs:
            issues.append(
                f"Page marker '{reference}' from the source document was turned into content"
            )
        else:
            issues.append(f"Unsupported page reference introduced: '{reference}'")

    return issues


# ---------------------------------------------------------------------
# Certainty and conditions
# ---------------------------------------------------------------------

def _contains_any(text: str, phrases: Sequence[str]) -> List[str]:
    lowered = text.lower()
    return [phrase for phrase in phrases if phrase in lowered]


def detect_certainty_issues(original_text: str, simplified_text: str) -> List[str]:
    """
    Detects qualifiers that were dropped, which turns a hedge into a promise.

    "normally announced in November/December" becoming "will be announced in
    November/December" states something the source never promised.
    """
    issues: List[str] = []
    if not original_text or not simplified_text:
        return issues

    original_hedges = _contains_any(original_text, FREQUENCY_HEDGES)
    if original_hedges and not _contains_any(simplified_text, FREQUENCY_HEDGES):
        definiteness = _contains_any(simplified_text, CERTAINTY_MARKERS)
        detail = (
            f" and the text now uses '{definiteness[0]}'"
            if definiteness
            else ""
        )
        issues.append(
            f"Certainty qualifier '{original_hedges[0]}' was dropped{detail}; "
            "the statement may no longer reflect how certain the source was"
        )

    original_conditions = _contains_any(original_text, CONDITION_PHRASES)
    if original_conditions and not CONDITION_CONSTRUCTION_RE.search(simplified_text):
        issues.append(
            f"Condition or exception '{original_conditions[0]}' was dropped from the simplified text"
        )

    return issues


# ---------------------------------------------------------------------
# Entity substitution
# ---------------------------------------------------------------------

def _terms_present(text: str, terms: Sequence[str]) -> Set[str]:
    lowered = text.lower()
    present: Set[str] = set()
    for term in terms:
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            present.add(term)
    return present


def detect_entity_issues(original_text: str, simplified_text: str) -> List[str]:
    """
    Detects one kind of organisation being replaced by another.

    A scholarship notice that talks about a "university/college/institute"
    must not come back as a "school": the eligibility of the reader changes.
    """
    issues: List[str] = []
    if not original_text or not simplified_text:
        return issues

    for family in ENTITY_FAMILIES:
        original_terms = _terms_present(original_text, family)
        simplified_terms = _terms_present(simplified_text, family)
        if not original_terms:
            continue

        dropped = original_terms - simplified_terms
        introduced = simplified_terms - original_terms
        if not dropped or not introduced:
            continue

        for dropped_term in sorted(dropped):
            for introduced_term in sorted(introduced):
                issues.append(
                    f"Entity changed: '{dropped_term}' in the source became "
                    f"'{introduced_term}' in the simplified text"
                )

    return issues


# ---------------------------------------------------------------------
# Unsupported numbers in obligations
# ---------------------------------------------------------------------

def _normalise_number(value: str) -> str:
    return value.replace(",", "").rstrip(".")


def detect_unsupported_number_issues(original_text: str, simplified_text: str) -> List[str]:
    """
    Detects obligations that quote a number the source never states.

    "You must declare on Page 4 of 7" invents the numbers 4 and 7 as
    requirements when the source only carried them as a page marker.
    """
    issues: List[str] = []
    if not original_text or not simplified_text:
        return issues

    original_body, _artifacts = strip_document_artifacts(original_text)
    original_numbers = {
        _normalise_number(number) for number in NUMBER_RE.findall(original_body)
    }

    for sentence in _split_sentences(simplified_text):
        if not OBLIGATION_RE.search(sentence):
            continue
        for number in NUMBER_RE.findall(sentence):
            if _normalise_number(number) not in original_numbers:
                issues.append(
                    f"Unsupported number '{number}' introduced in an obligation: "
                    f"\"{sentence[:120]}\""
                )
                break

    return issues


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

def _content_words(text: str) -> List[str]:
    """The words of a rule that carry its meaning."""
    stop_words = {
        "the", "and", "for", "that", "this", "with", "from", "have", "has", "had",
        "are", "was", "were", "been", "being", "will", "shall", "must", "may",
        "can", "not", "any", "all", "his", "her", "its", "their", "who", "which",
        "when", "where", "while", "such", "only", "also", "than", "then", "them",
        "they", "you", "your", "our", "per", "via", "under", "upon", "into", "out",
        "does", "did", "each", "other", "more", "most", "same", "one", "two",
        "there", "here", "what", "how", "his", "her", "its", "he", "she",
    }
    words = re.findall(r"[a-z0-9%]+", text.lower())
    return [word for word in words if len(word) > 2 and word not in stop_words]


def detect_missing_rules(original_text: str, simplified_text: str) -> List[str]:
    """
    Finds rules of the source that do not appear in the simplified text.

    A model that rewrites a document can quietly leave a rule out. Every rule
    has words that only it uses - "acquired", "AISHE", "nodal" - and those
    have to survive the rewrite. A rule that is only reworded keeps them, so
    a paraphrase is not reported - only a rule whose content is really gone.
    """
    if not original_text or not simplified_text:
        return []

    from app.services.extraction_service import (
        extract_eligibility_requirements,
        extract_important_conditions,
    )

    rules = [
        rule.requirement for rule in extract_eligibility_requirements(original_text)
    ] + [condition.condition for condition in extract_important_conditions(original_text)]

    if not rules:
        return []

    simplified_lower = simplified_text.lower()
    missing: List[str] = []

    for rule in rules:
        words = _content_words(rule)
        if len(words) < 4:
            continue
        present = sum(1 for word in words if word in simplified_lower)
        # A rule is only reported when almost none of its content survived.
        # A reworded rule keeps most of its words, so a paraphrase is not
        # reported - only a rule that is really gone.
        if present * 10 < len(words) * 4:
            missing.append(
                f"A rule from the source seems to be missing from the simplified text: "
                f"{rule[:160]}"
            )

    return missing[:3]


def validate_fidelity(original_text: str, simplified_text: str) -> List[str]:
    """
    Runs every fidelity check and returns the issues found.

    An empty list means nothing obviously unsupported was detected. It is not
    a guarantee that the simplified text is legally equivalent to the source.
    """
    issues: List[str] = []
    issues.extend(detect_page_reference_issues(original_text, simplified_text))
    issues.extend(detect_certainty_issues(original_text, simplified_text))
    issues.extend(detect_entity_issues(original_text, simplified_text))
    issues.extend(detect_unsupported_number_issues(original_text, simplified_text))
    issues.extend(detect_missing_rules(original_text, simplified_text))

    # Keep the report readable when the same problem repeats.
    unique: List[str] = []
    for issue in issues:
        if issue not in unique:
            unique.append(issue)
    return unique
