"""
Regression tests for the quality of the Instant Summary.

The fixture is the complete scholarship notice. These tests check that the
summary shows meaningful, non-duplicated and correctly ranked facts.
"""

from pathlib import Path

import pytest

from app.services.extraction_service import extract_structured_information
from app.services.summary_service import build_instant_summary

FIXTURE = Path(__file__).parent / "fixtures" / "scholarship_terms.txt"
SOURCE = FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def summary():
    info = extract_structured_information(SOURCE)
    return build_instant_summary(info)


def values(summary):
    return [item["value"] for item in summary["items"]]


def labels(summary):
    return [item["label"] for item in summary["items"]]


class TestContextualPercentages:
    """A percentage is never shown without its meaning"""

    def test_the_reservation_has_a_meaningful_label(self, summary):
        reservations = [
            item for item in summary["items"] if "%" in item["value"] and "women" in item["value"].lower()
        ]

        assert reservations, "the reservation for women must be reported"
        assert reservations[0]["label"] == "Reservation"
        assert "30%" in reservations[0]["value"]

    def test_the_subject_allocation_has_a_meaningful_label(self, summary):
        allocations = [
            item for item in summary["items"]
            if item["label"] == "Subject allocation"
        ]

        assert allocations, "the subject allocation must be reported"
        assert "50%" in allocations[0]["value"]

    def test_no_bare_percentage_is_shown(self, summary):
        for item in summary["items"]:
            if item["kind"] != "percentage":
                continue
            # The value explains what the percentage is about.
            assert item["value"] != item["value"].split()[0]
            assert len(item["value"]) > 10

    def test_a_percentage_without_a_context_is_not_shown_alone(self):
        info = extract_structured_information("The scheme covers 25% of the applicants.")
        result = build_instant_summary(info)

        for item in result["items"]:
            if item["kind"] == "percentage":
                assert len(item["value"]) > 3
                assert item["value"] != "25%"


class TestContextualAmounts:
    """An amount is never shown without its meaning"""

    def test_the_scholarship_amount_gets_a_meaningful_label(self):
        info = extract_structured_information(
            "The scholarship amount is Rs. 2,50,000 per annum and is paid in two instalments."
        )
        result = build_instant_summary(info)

        amounts = [item for item in result["items"] if item["kind"] == "money"]
        assert amounts
        assert amounts[0]["label"] == "Scholarship amount"
        assert "2,50,000" in amounts[0]["value"]
        assert "per annum" in amounts[0]["value"]

    def test_a_fee_gets_its_own_label(self):
        info = extract_structured_information(
            "The applicant must pay a processing fee of ₹500 within 30 days."
        )
        result = build_instant_summary(info)

        amounts = [item for item in result["items"] if item["kind"] == "money"]
        assert amounts
        assert amounts[0]["label"] == "Fee"


class TestNoDuplicateFacts:
    """The same fact is only shown once"""

    def test_the_age_appears_only_once(self, summary):
        age_facts = [item for item in summary["items"] if item["kind"] == "age"]

        assert len(age_facts) == 1
        assert age_facts[0]["value"] == "Below 30 years"

        # No other bullet repeats the age rule.
        for item in summary["items"]:
            if item["kind"] == "age":
                continue
            assert "below the age of 30" not in item["value"].lower()

    def test_the_values_are_unique(self, summary):
        assert len(values(summary)) == len(set(values(summary)))

    def test_a_restatement_is_removed(self, summary):
        """A rule that only repeats the age rule is not shown again."""
        restatements = [
            item for item in summary["items"]
            if item["kind"] == "eligibility" and "30" in item["value"]
        ]

        assert restatements == []

    def test_no_label_is_repeated_inside_its_value(self, summary):
        for item in summary["items"]:
            assert not item["value"].lower().startswith(f"{item['label'].lower()}:")


class TestImportantFactsComeFirst:
    """The conditions that matter are not pushed out by generic facts"""

    def test_the_one_scholarship_rule_is_shown(self, summary):
        joined = " ".join(values(summary)).lower()

        assert "only one scholarship" in joined

    def test_the_restriction_on_other_benefits_is_shown(self, summary):
        joined = " ".join(values(summary)).lower()

        assert "shall not accept" in joined or "must not accept" in joined

    def test_the_noc_exception_is_shown(self, summary):
        joined = " ".join(values(summary)).lower()

        assert "noc" in joined

    def test_the_relinquishment_is_shown(self, summary):
        joined = " ".join(values(summary)).lower()

        assert "relinquish" in joined or "give up" in joined

    def test_the_declaration_is_shown(self, summary):
        joined = " ".join(values(summary)).lower()

        assert "declare" in joined

    def test_the_important_conditions_are_not_hidden_by_generic_facts(self, summary):
        """The important conditions come before the general ones."""
        condition_positions = [
            index
            for index, item in enumerate(summary["items"])
            if item["kind"] == "condition"
        ]

        assert condition_positions
        # A condition that states a restriction is shown before a plain one.
        joined = [summary["items"][index]["value"].lower() for index in condition_positions]
        first = joined[0]
        assert any(
            hint in first
            for hint in ("only one", "shall not", "must not", "not required", "relinquish", "declare", "mandatory")
        )


class TestHiddenCount:
    """The hidden count counts the facts that really did not fit"""

    def test_the_count_only_counts_omitted_unique_facts(self, summary):
        assert summary["hidden"] == summary["total"] - len(summary["items"])
        assert summary["hidden"] >= 0

    def test_the_count_is_not_larger_than_the_number_of_facts(self, summary):
        info = extract_structured_information(SOURCE)
        unique = {
            requirement.requirement for requirement in info.eligibility_requirements
        } | {condition.condition for condition in info.important_conditions}

        assert summary["total"] <= len(unique)
        assert summary["hidden"] <= len(unique)

    def test_the_omitted_facts_are_still_available(self, summary):
        """A fact that does not fit in the card is still extracted."""
        info = extract_structured_information(SOURCE)
        everything = " ".join(
            requirement.requirement for requirement in info.eligibility_requirements
        ) + " ".join(condition.condition for condition in info.important_conditions)

        # A rule that the summary leaves out is still in the extraction.
        assert "institution" in everything.lower()
        assert "tie" in everything.lower() or "marks" in everything.lower()


class TestNothingMeaningless:
    """No fragments, headings or page markers"""

    def test_no_page_marker_is_shown(self, summary):
        for value in values(summary):
            assert "Page 3 of 7" not in value
            assert "Page 4 of 7" not in value

    def test_no_heading_is_shown(self, summary):
        for value in values(summary):
            assert value.strip() != "TYPES OF INSTITUTION"
            assert value.strip() != "ELIGIBILITY"
            assert not value.strip().endswith(":")

    def test_no_fragment_starts_with_punctuation(self, summary):
        for value in values(summary):
            assert not value.startswith((",", ";", ":"))

    def test_the_negation_is_kept(self, summary):
        negative = [item for item in summary["items"] if item["label"] == "Not eligible"]

        assert negative
        for item in negative:
            assert "not eligible" in item["value"].lower()
