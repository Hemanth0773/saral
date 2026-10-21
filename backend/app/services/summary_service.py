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
    "shortlist",
    "short-listed",
    "short listed",
    "reservation",
    "reserved for",
    "tie",
    "ranking",
)

# What a percentage is about. The first match wins.
PERCENTAGE_LABELS: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    (("reserv", "quot"), "Reservation"),
    (("earmark", "set aside", "setaside", "allocat"), "Subject allocation"),
    (("interest",), "Interest rate"),
    (("discount",), "Discount"),
    (("tax",), "Tax"),
    (("attendance",), "Attendance"),
    (("mark", "score"), "Marks"),
    (("fee",), "Fee"),
    (("budget", "amount"), "Budget"),
)

# The order in which the facts matter. A deadline, a document to send or a
# rule the reader must not break comes before a step of the procedure.
FACT_PRIORITY: Dict[str, float] = {
    "deadline": 0.0,
    "age": 1.0,
    "money": 2.0,
    "document": 3.0,
    "percentage": 4.0,
    "condition": 5.0,
    "eligibility": 7.0,
    "procedure": 9.0,
    "contact": 10.0,
    "date": 11.0,
}

# A rule that does not apply is shown before a positive rule.
NEGATED_RULE_PRIORITY = 6.0

# A condition that states a restriction, an exception or a duty matters more
# than a plain observation.
IMPORTANT_CONDITION_PRIORITY = 5.0
MINOR_CONDITION_PRIORITY = 8.0

# A condition that states a restriction, an exception or a duty matters more
# than a plain observation.
IMPORTANT_CONDITION_HINTS = (
    "only one",
    "shall not",
    "must not",
    "not required",
    "not permitted",
    "not be allowed",
    "noc",
    "relinquish",
    "give up",
    "cancel",
    "declare that",
    "prohibited",
    "forfeit",
    "not eligible",
    "ineligible",
    "mandatory",
    "compulsory",
    "obligatory",
    "is required",
    "are required",
    "must have",
    "shall have",
)

# Words that carry no meaning when two facts are compared.
_STOP_WORDS = {    "the", "and", "for", "that", "this", "with", "from", "have", "has", "had",
    "are", "was", "were", "been", "being", "will", "shall", "must", "may", "can",
    "not", "any", "all", "his", "her", "its", "their", "who", "which", "when",
    "where", "while", "such", "only", "also", "than", "then", "them", "they",
    "you", "your", "our", "its", "per", "via", "under", "upon", "into", "out",
    "shall", "does", "did", "been", "being", "each", "other", "more", "most",
    "such", "same", "one", "two", "three", "there", "here", "what", "how",
}

# Phrases that mark a rule. Two facts that both contain the same phrase state
# the same rule in different words.
_RULE_MARKER_PHRASES = (
    "shall not accept",
    "must not accept",
    "not accept any other",
    "only one scholarship",
    "not be in receipt",
    "in receipt of any",
    "not required to obtain",
    "required to tender",
    "shall have to relinquish",
    "declare that",
    "subject to the condition",
    "not eligible to apply",
)

# The directions an age rule can have. A rule that repeats the number and the
# direction of an age that already has its own bullet is a restatement.
_AGE_DIRECTIONS = (
    "below",
    "under",
    "less than",
    "not more than",
    "at most",
    "maximum",
    "above",
    "over",
    "more than",
    "at least",
    "minimum",
    "or older",
    "or younger",
)

# A money amount gets a label that says what the money is for.
MONEY_LABELS: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    (("scholarship",), "Scholarship amount"),
    (("stipend",), "Stipend"),
    (("assistance",), "Assistance amount"),
    (("fee", "fees"), "Fee"),
    (("interest",), "Interest"),
    (("loan",), "Loan amount"),
    (("salary",), "Salary"),
    (("grant",), "Grant amount"),
    (("pension",), "Pension"),
    (("penalty", "fine"), "Penalty"),
    (("tuition",), "Tuition"),
    (("travel", "allowance"), "Allowance"),
)

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


def _significant_words(text: str) -> Set[str]:
    """The words of a fact that carry its meaning."""
    words = re.findall(r"[a-z0-9%]+", text.lower())
    return {word for word in words if len(word) > 2 and word not in _STOP_WORDS}


def _is_similar(candidate: str, existing: str) -> bool:
    """
    True when two facts say the same thing in different words.

    "The student must declare that he shall not accept any other monetary
    benefit" and "In other words, a student ... shall not accept any other
    scholarship ... or receive any emoluments" explain the same rule, and
    showing both makes the summary longer without adding anything.
    """
    candidate_words = _significant_words(candidate)
    other_words = _significant_words(existing)

    if len(candidate_words) < 5 or len(other_words) < 5:
        return False

    shared = candidate_words & other_words
    union = candidate_words | other_words
    if not union:
        return False

    similarity = len(shared) / len(union)
    if similarity >= 0.6:
        return True

    # Two sentences that state the same rule with different wording share a
    # distinctive phrase.
    if len(shared) >= 5:
        candidate_lower = candidate.lower()
        other_lower = existing.lower()
        if any(
            marker in candidate_lower and marker in other_lower
            for marker in _RULE_MARKER_PHRASES
        ):
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


def _money_label_and_value(amount) -> Tuple[str, str]:
    """
    Turns an amount into a fact that says what the money is for.

    "2,50,000" on its own does not tell a reader whether it is a scholarship,
    a fee or a loan.
    """
    context = re.sub(r"\s+", " ", (amount.purpose or "").strip())
    value = amount.amount

    label = "Amount"
    lowered = context.lower()
    for hints, candidate_label in MONEY_LABELS:
        if any(hint in lowered for hint in hints):
            label = candidate_label
            break

    if context:
        # The clause starts with the currency and the number, for example
        # "Rs. 2,50,000 per annum".
        remainder = re.sub(r"^(?:rs\.?|inr|₹)\s*", "", context, flags=re.IGNORECASE)
        number = re.sub(r"^(?:rs\.?|inr|₹)\s*", "", value, flags=re.IGNORECASE)

        if remainder.lower().startswith(number.lower()):
            tail = remainder[len(number):].strip()
            if tail.lower().startswith("of "):
                value = f"{value} {tail}"
            elif tail:
                value = f"{value} of {tail}"
        elif number.lower() in remainder.lower():
            tail = remainder[remainder.lower().index(number.lower()) + len(number):].strip()
            value = f"{value} {tail}" if tail else value
        else:
            value = f"{value} - {context}"

    return label, value


def _percentage_label_and_value(percentage) -> Tuple[str, str]:
    """
    Turns a percentage into a fact that says what it is about.

    "30%" on its own is not a fact. The clause it sits in - "30% slots will
    be reserved for the women candidates" - is.
    """
    context = re.sub(r"\s+", " ", (percentage.purpose or "").strip())
    value = percentage.percentage

    label = "Percentage"
    lowered = context.lower()
    for hints, candidate_label in PERCENTAGE_LABELS:
        if any(hint in lowered for hint in hints):
            label = candidate_label
            break

    if context:
        lowered_context = context.lower()
        if lowered_context.startswith(value.lower()):
            remainder = context[len(value):].strip()
            if remainder.lower().startswith("of "):
                value = f"{value} {remainder}"
            elif remainder:
                value = f"{value} of {remainder}"
        elif value.lower() in lowered_context:
            # The percentage sits inside the clause ("other 50% are earmarked
            # for Science"), so what follows it is the meaning.
            remainder = context[lowered_context.index(value.lower()) + len(value):].strip()
            value = f"{value} {remainder}" if remainder else value
        else:
            value = f"{value} - {context}"

    return label, value


def _is_important_condition(value: str) -> bool:
    """A restriction, an exception or a duty matters more than a remark."""
    lowered = value.lower()
    return any(hint in lowered for hint in IMPORTANT_CONDITION_HINTS)


def build_instant_summary(
    structured_info: Optional[StructuredInformation],
    preserved_facts: Optional[List[PreservedFact]] = None,
    limit: int = MAX_SUMMARY_ITEMS,
) -> Dict[str, Any]:
    """
    Builds the canonical Instant Summary.

    The facts are de-duplicated, ranked by how much they matter to the reader
    and only then limited to what the card can show. The number of hidden
    facts counts the unique facts that really did not fit.

    Args:
        structured_info: The structured extraction of the source document
        preserved_facts: The facts the simplification had to preserve
        limit: Maximum number of bullets

    Returns:
        A dictionary with:
        - ``items``: the bullets to render, as
          ``{id, kind, label, value, severity}`` items, already de-duplicated
          and free of page markers, headings and fragments
        - ``total``: how many unique, trustworthy facts were found
        - ``hidden``: how many of them did not fit into the summary
    """
    candidates: List[Dict[str, Any]] = []
    shown: List[str] = []
    precise_values: List[str] = []
    age_numbers: List[str] = []
    order = 0

    def restates_a_precise_fact(cleaned: str) -> bool:
        """
        True when the text only repeats a fact that has its own bullet.

        The age rule is the common case: "Only students who are below the age
        of 30 years ... are eligible to apply" repeats the age requirement,
        and showing both says the same thing twice.
        """
        for precise in precise_values:
            if precise.lower() in cleaned.lower():
                return True

        lowered = cleaned.lower()
        for number in age_numbers:
            if number in lowered and any(
                direction in lowered for direction in _AGE_DIRECTIONS
            ):
                return True

        return False

    def add(
        item_id: str,
        kind: str,
        label: str,
        value: str,
        severity: str = "info",
        priority: Optional[float] = None,
    ) -> None:
        nonlocal order

        cleaned = value.strip()
        if not _is_usable(cleaned):
            return
        if _is_heading(cleaned):
            return
        # A line that introduces a list is not a fact of its own.
        if cleaned.endswith(":"):
            return
        if _is_duplicate(cleaned, shown):
            return
        if any(_is_similar(cleaned, other) for other in shown):
            return
        # A rule that only restates a fact that already has its own bullet
        # ("must be under 30 years" next to "Age requirement: under 30 years")
        # is dropped, so the same fact is not reported twice.
        if kind in ("eligibility", "condition", "procedure"):
            if restates_a_precise_fact(cleaned):
                return

        shown.append(cleaned)
        candidates.append({
            "id": item_id,
            "kind": kind,
            "label": label,
            "value": cleaned,
            "severity": severity,
            "priority": FACT_PRIORITY.get(kind, 9.0) if priority is None else priority,
            "order": order,
        })
        order += 1

    if not structured_info:
        return {"items": [], "total": 0, "hidden": 0}

    # The facts are collected first and ranked afterwards, so an important
    # condition is never pushed out by a generic one.
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
        label, value = _money_label_and_value(amount)
        add(f"money-{index}", "money", label, value)
        precise_values.append(amount.amount)

    for index, age in enumerate(structured_info.age_requirements or []):
        value = format_age_requirement(age)
        add(f"age-{index}", "age", "Age requirement", value)
        if value:
            precise_values.append(value)
            age_numbers.extend(re.findall(r"\d+", value))

    for index, percentage in enumerate(structured_info.percentages or []):
        label, value = _percentage_label_and_value(percentage)
        # Two percentages that mean the same thing - the two halves of a 50/50
        # split - are shown as one fact.
        existing = next(
            (
                item
                for item in candidates
                if item["kind"] == "percentage" and item["label"] == label
            ),
            None,
        )
        if existing is not None:
            if value not in existing["value"]:
                existing["value"] = f"{existing['value']}; {value}"
            continue
        add(f"percentage-{index}", "percentage", label, value)
        precise_values.append(percentage.percentage)

    for index, requirement in enumerate(structured_info.eligibility_requirements or []):
        category = (requirement.category or "").strip()
        if category:
            # The backend already decided what kind of rule this is, for
            # example a rule that does not apply.
            label = category
        else:
            lowered = requirement.requirement.lower()
            label = "Selection" if any(hint in lowered for hint in SELECTION_HINTS) else "Eligibility"

        # A rule that restricts or forbids something matters as much as a
        # condition, and a rule that does not apply comes before a positive
        # one.
        if category == "Not eligible":
            priority = NEGATED_RULE_PRIORITY
        elif _is_important_condition(requirement.requirement):
            priority = IMPORTANT_CONDITION_PRIORITY
        else:
            priority = 7.0
        add(
            f"eligibility-{index}",
            "eligibility",
            label,
            requirement.requirement,
            priority=priority,
        )

    for index, procedure in enumerate(structured_info.application_procedure or []):
        label = f"Step {procedure.step_number}" if procedure.step_number else "Application process"
        add(f"procedure-{index}", "procedure", label, procedure.description)

    for index, condition in enumerate(structured_info.important_conditions or []):
        condition_type = (condition.type or "").lower()
        lowered = condition.condition.lower()
        if any(hint in lowered for hint in SELECTION_HINTS):
            # A rule about how the candidates are chosen.
            label = "Selection"
        elif condition_type == "exception":
            label = "Exception"
        elif condition_type == "warning":
            label = "Warning"
        else:
            label = "Conditions"
        severity = "warning" if condition_type == "warning" else "info"
        add(
            f"condition-{index}",
            "condition",
            label,
            condition.condition,
            severity,
            priority=(
                IMPORTANT_CONDITION_PRIORITY
                if _is_important_condition(condition.condition)
                else MINOR_CONDITION_PRIORITY
            ),
        )

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

    # The facts are ranked before the limit is applied, so the important ones
    # are always the ones that are shown.
    candidates.sort(key=lambda item: (item["priority"], item["order"]))

    # The procedure steps are capped, so a long list of steps does not push
    # the other facts out.
    procedure_seen = 0
    kept: List[Dict[str, Any]] = []
    for item in candidates:
        if item["kind"] == "procedure":
            if procedure_seen >= MAX_PROCEDURE_STEPS:
                continue
            procedure_seen += 1
        kept.append(item)

    items = kept[:limit]
    for item in items:
        item.pop("priority", None)
        item.pop("order", None)

    # The hidden count is the number of unique facts that really did not fit.
    total = len(candidates)
    return {
        "items": items,
        "total": total,
        "hidden": max(0, total - len(items)),
    }
