"""
Canonical Instant Summary.

The website and the Chrome extension show the same summary, so it is built
here, once, in the backend. Both interfaces render the result of this module
and therefore cannot disagree about what a document says.

The summary only contains facts that the backend could actually extract from
the source document. Anything that cannot be read with confidence - a page
marker, a section heading, a sentence fragment, a statement that repeats an
earlier one - is left out rather than shown.
"""

import re
from typing import Any, Dict, List, Optional

from app.schemas.extraction import (
    ExtractedAgeRequirement,
    StructuredInformation,
)
from app.schemas.simplification import PreservedFact

# Maximum number of bullets in the summary.
MAX_SUMMARY_ITEMS = 12

# Maximum number of document names shown in one bullet.
MAX_DOCUMENT_NAMES = 5

# Maximum number of procedure steps shown. A notice can list many steps, and
# showing all of them would push the other facts out of the summary.
MAX_PROCEDURE_STEPS = 4

# Maximum number of eligibility rules shown, for the same reason.
MAX_ELIGIBILITY_RULES = 4

# A standalone pagination marker such as "Page 5 of 7" is never a fact.
PAGE_MARKER_RE = re.compile(
    r"^\s*pages?\s+\d+(?:\s*(?:of|out\s+of|/)\s+\d+)?\s*\.?\s*$",
    re.IGNORECASE,
)

# A heading such as "PROCEDURE FOR AVAILING THE SCHOLARSHIP" is not a fact.
ALL_CAPS_HEADING_RE = re.compile(r"^[A-Z][A-Z ,.'()/&-]*$")

# Words that show a statement is about how candidates are selected.
SELECTION_HINTS = (
    "merit",
    "selection",
    "selected",
    "shortlist",
    "short-listed",
    "short listed",
    "reservation",
    "reserved",
    "tie",
    "ranking",
)

# A money amount gets a label that says what the money is for.
MONEY_LABELS = {
    "scholarship": "Scholarship amount",
    "assistance": "Assistance amount",
    "stipend": "Stipend",
    "fee": "Fee",
    "interest": "Interest",
    "loan": "Loan amount",
    "salary": "Salary",
    "grant": "Grant amount",
    "penalty": "Penalty",
    "fines": "Penalty",
}

PERCENTAGE_LABELS = {
    "interest": "Interest rate",
    "discount": "Discount",
    "tax": "Tax",
    "reservation": "Reservation",
    "reservations": "Reservation",
    "attendance": "Attendance",
    "marks": "Marks",
    "score": "Score",
    "percentage": "Percentage",
}

# Qualifiers that follow the number, e.g. "30 years or older".
_TRAILING_QUALIFIERS = ("or older", "or above", "or more", "and above")
_LEADING_QUALIFIERS = (
    "under", "below", "less than", "not more than", "not above", "not exceeding",
    "up to", "within", "at least", "not less than", "no less than", "over",
    "above", "more than", "exceeding",
)


def _is_page_marker(value: str) -> bool:
    return bool(PAGE_MARKER_RE.match(value.strip()))


def _is_heading(value: str) -> bool:
    trimmed = value.strip()
    if len(trimmed) < 5:
        return False
    if any(char.isdigit() for char in trimmed):
        return False
    if not ALL_CAPS_HEADING_RE.match(trimmed):
        return False
    return " " in trimmed


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s₹%]", " ", value.lower())).strip()


def _is_duplicate(candidate: str, existing: List[str]) -> bool:
    """True when the candidate says the same thing as something already shown."""
    normalised = _normalise(candidate)
    if not normalised:
        return False

    for other in existing:
        other_normalised = _normalise(other)
        if not other_normalised:
            continue
        if normalised == other_normalised:
            return True
        # Only compare full sentences, never short labels such as "Aadhaar".
        if len(normalised) < 20 or len(other_normalised) < 20:
            continue
        if normalised in other_normalised or other_normalised in normalised:
            return True

    return False


def _is_usable(value: str) -> bool:
    trimmed = value.strip()
    if len(trimmed) < 4:
        # A short value can still be a fact when it carries a number, for
        # example the percentage "30%".
        if not re.search(r"\d", trimmed):
            return False
    if _is_page_marker(trimmed):
        return False
    return bool(re.search(r"[a-z0-9]", trimmed, re.IGNORECASE))


def format_age_requirement(requirement: ExtractedAgeRequirement) -> str:
    """
    Formats an age rule so its direction survives.

    "below the age of 30 years" stays an upper bound and "30 years or older"
    stays a lower bound; neither is turned into "30+ years".
    """
    qualifier = re.sub(r"\s+", " ", (requirement.qualifier or "").strip())
    minimum = requirement.minimum_age
    maximum = requirement.maximum_age

    if minimum is not None and maximum is not None:
        return f"{minimum}-{maximum} years"

    if minimum is not None:
        if qualifier in _TRAILING_QUALIFIERS:
            return f"{minimum} years {qualifier}"
        if qualifier:
            return f"{qualifier[0].upper()}{qualifier[1:]} {minimum} years"
        return f"{minimum}+ years"

    if maximum is not None:
        if qualifier in _TRAILING_QUALIFIERS:
            return f"{maximum} years {qualifier}"
        if qualifier:
            return f"{qualifier[0].upper()}{qualifier[1:]} {maximum} years"
        return f"Up to {maximum} years"

    return ""


def _purpose_label(purpose: Optional[str], table: Dict[str, str], fallback: str) -> str:
    if not purpose:
        return fallback
    return table.get(purpose.strip().lower(), fallback)


def build_instant_summary(
    structured_info: Optional[StructuredInformation],
    preserved_facts: Optional[List[PreservedFact]] = None,
    limit: int = MAX_SUMMARY_ITEMS,
) -> Dict[str, Any]:
    """
    Builds the canonical Instant Summary.

    Args:
        structured_info: The structured extraction of the source document
        preserved_facts: The facts the simplification had to preserve
        limit: Maximum number of bullets

    Returns:
        A dictionary with:
        - ``items``: the bullets to render, as
          ``{id, kind, label, value, severity}`` items, already de-duplicated
          and free of page markers, headings and fragments
        - ``total``: how many trustworthy facts were found
        - ``hidden``: how many did not fit into the summary
    """
    candidates: List[Dict[str, Any]] = []
    shown: List[str] = []
    precise_values: List[str] = []
    procedure_count = 0
    skipped_steps = 0
    skipped_rules = 0

    def add(item_id: str, kind: str, label: str, value: str, severity: str = "info") -> None:
        cleaned = value.strip()
        if not _is_usable(cleaned):
            return
        if _is_heading(cleaned):
            return
        if _is_duplicate(cleaned, shown):
            return
        # A rule that only restates a fact that already has its own bullet
        # ("must be under 30 years" next to "Age requirement: under 30 years")
        # is dropped, so the same fact is not reported twice.
        if kind in ("eligibility", "condition", "procedure"):
            if any(precise and precise.lower() in cleaned.lower() for precise in precise_values):
                return
        shown.append(cleaned)
        candidates.append({
            "id": item_id,
            "kind": kind,
            "label": label,
            "value": cleaned,
            "severity": severity,
        })

    if not structured_info:
        return {"items": [], "total": 0, "hidden": 0}

    # The order is the order a reader needs the facts in: when, what to send,
    # how much, who qualifies, what the restrictions are, how to apply.
    for index, deadline in enumerate(structured_info.deadlines or []):
        add(f"deadline-{index}", "deadline", "Deadline", deadline.date, "critical")
        precise_values.append(deadline.date)

    documents = [doc.name for doc in (structured_info.required_documents or []) if doc.name]
    if documents:
        if len(documents) > MAX_DOCUMENT_NAMES:
            shown_names = ", ".join(documents[:MAX_DOCUMENT_NAMES])
            value = f"{shown_names} and {len(documents) - MAX_DOCUMENT_NAMES} more"
        else:
            value = ", ".join(documents)
        add("documents", "document", "Documents needed", value)

    for index, amount in enumerate(structured_info.financial_information or []):
        label = _purpose_label(amount.purpose, MONEY_LABELS, "Amount")
        add(f"money-{index}", "money", label, amount.amount)
        precise_values.append(amount.amount)

    for index, age in enumerate(structured_info.age_requirements or []):
        value = format_age_requirement(age)
        add(f"age-{index}", "age", "Age requirement", value)
        if value:
            precise_values.append(value)

    for index, percentage in enumerate(structured_info.percentages or []):
        label = _purpose_label(percentage.purpose, PERCENTAGE_LABELS, "Percentage")
        add(f"percentage-{index}", "percentage", label, percentage.percentage)

    eligibility_count = 0
    for index, requirement in enumerate(structured_info.eligibility_requirements or []):
        category = (requirement.category or "").strip()
        if category:
            # The backend already decided what kind of rule this is, for
            # example a rule that does not apply.
            label = category
        else:
            lowered = requirement.requirement.lower()
            label = "Selection" if any(hint in lowered for hint in SELECTION_HINTS) else "Eligibility"

        if eligibility_count >= MAX_ELIGIBILITY_RULES:
            skipped_rules += 1
            continue
        add(f"eligibility-{index}", "eligibility", label, requirement.requirement)
        eligibility_count += 1

    # The procedure comes before the conditions, so a numbered step keeps its
    # own label instead of also appearing as a condition.
    for index, procedure in enumerate(structured_info.application_procedure or []):
        label = f"Step {procedure.step_number}" if procedure.step_number else "Application process"
        if procedure_count >= MAX_PROCEDURE_STEPS:
            skipped_steps += 1
            continue
        add(f"procedure-{index}", "procedure", label, procedure.description)
        procedure_count += 1

    for index, condition in enumerate(structured_info.important_conditions or []):
        condition_type = (condition.type or "").lower()
        if condition_type == "exception":
            label = "Exception"
        elif condition_type == "warning":
            label = "Warning"
        else:
            label = "Conditions"
        severity = "warning" if condition_type == "warning" else "info"
        add(f"condition-{index}", "condition", label, condition.condition, severity)

    for index, contact in enumerate(structured_info.contact_information or []):
        label = contact.type.strip().capitalize() if contact.type else "Contact"
        add(f"contact-{index}", "contact", label, contact.value)

    for index, date in enumerate(structured_info.important_dates or []):
        add(f"date-{index}", "date", "Important date", date.date)

    # The facts the simplification had to preserve are only used when the
    # structured extraction did not already cover that kind of fact.
    covered = {item["kind"] for item in candidates}
    for index, fact in enumerate(preserved_facts or []):
        kind = {
            "deadline": "deadline",
            "money": "money",
            "percentage": "percentage",
            "age": "age",
            "contact": "contact",
        }.get(fact.fact_type)
        if kind is None or kind in covered:
            continue
        label = {
            "deadline": "Deadline",
            "money": "Amount",
            "percentage": "Percentage",
            "age": "Age requirement",
            "contact": "Contact",
        }[kind]
        severity = "info" if fact.preserved_in_simplified else "warning"
        add(f"preserved-{index}", kind, label, fact.value, severity)

    # The steps and the rules that did not fit are counted as hidden, so the
    # interface can report that the document contains more.
    total = len(candidates) + skipped_steps + skipped_rules

    # Keep the procedure steps short, then apply the overall limit.
    procedure_seen = 0
    kept: List[Dict[str, Any]] = []
    for item in candidates:
        if item["kind"] == "procedure":
            if procedure_seen >= MAX_PROCEDURE_STEPS:
                continue
            procedure_seen += 1
        kept.append(item)

    items = kept[:limit]
    return {
        "items": items,
        "total": total,
        "hidden": max(0, total - len(items)),
    }
