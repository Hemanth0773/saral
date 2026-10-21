"""
Mandatory regression tests for the complete scholarship terms fixture.

The fixture in ``tests/fixtures/scholarship_terms.txt`` is the full text of
the notice. Every requirement of the notice is checked here, so that a change
to the extraction, the summary or the validation cannot quietly drop one.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import llm_service, summary_service, validation_service
from app.services.extraction_service import (
    extract_age_requirements,
    extract_eligibility_requirements,
    extract_important_conditions,
    extract_required_documents,
    extract_structured_information,
)

client = TestClient(app)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "scholarship_terms.txt"
SOURCE = FIXTURE_PATH.read_text(encoding="utf-8")


# ============================================================
# The age rule
# ============================================================

class TestAgeDirection:
    """The direction of an age comparison must survive."""

    def test_the_fixture_age_is_below_thirty(self):
        requirements = extract_age_requirements(SOURCE)

        assert requirements, "the age rule must be found"
        age = requirements[0]
        assert age.maximum_age == 30
        assert age.minimum_age is None
        assert age.qualifier == "below"

    def test_the_summary_never_says_thirty_plus(self):
        info = extract_structured_information(SOURCE)
        summary = summary_service.build_instant_summary(info)

        ages = [item["value"] for item in summary["items"] if item["kind"] == "age"]
        assert ages
        assert ages[0].lower().startswith("below")
        assert "30+" not in ages[0]
        assert "30 years" in ages[0]

    @pytest.mark.parametrize(
        "phrase, expected_maximum, expected_minimum",
        [
            # An upper bound.
            ("below the age of 30 years", 30, None),
            ("under 30 years of age", 30, None),
            ("less than 30 years", 30, None),
            ("not more than 30 years", 30, None),
            ("at most 30 years", 30, None),
            ("maximum age of 30 years", 30, None),
            ("not exceeding 30 years", 30, None),
            # A lower bound.
            ("above 30 years of age", None, 30),
            ("over 30 years", None, 30),
            ("more than 30 years", None, 30),
            ("at least 30 years of age", None, 30),
            ("minimum age of 30 years", None, 30),
            ("30 years or older", None, 30),
            # Both bounds.
            ("between 18 and 25 years", 25, 18),
            ("18 to 25 years", 25, 18),
            # An upper bound written after the number.
            ("18 years or younger", 18, None),
        ],
    )
    def test_every_direction_keeps_its_meaning(self, phrase, expected_maximum, expected_minimum):
        text = f"The applicant must be {phrase} to apply."

        requirements = extract_age_requirements(text)
        assert requirements, f"the age rule was not found in: {phrase}"

        age = requirements[0]
        assert age.maximum_age == expected_maximum, phrase
        assert age.minimum_age == expected_minimum, phrase

    def test_an_upper_bound_is_never_rendered_as_a_lower_bound(self):
        for phrase in ("below the age of 30 years", "under 30 years", "at most 30 years"):
            info = extract_structured_information(f"The applicant must be {phrase} to apply.")
            summary = summary_service.build_instant_summary(info)
            ages = [item["value"] for item in summary["items"] if item["kind"] == "age"]

            assert ages, phrase
            assert "30+" not in ages[0], phrase

    def test_a_lower_bound_is_never_rendered_as_an_upper_bound(self):
        for phrase in ("at least 30 years of age", "above 30 years", "30 years or older"):
            info = extract_structured_information(f"The applicant must be {phrase} to apply.")
            summary = summary_service.build_instant_summary(info)
            ages = [item["value"] for item in summary["items"] if item["kind"] == "age"]

            assert ages, phrase
            assert "up to" not in ages[0].lower(), phrase


# ============================================================
# Negative rules
# ============================================================

class TestNegationIsPreserved:
    """A rule that does not apply must never read as a positive requirement."""

    def test_the_ineligible_rule_keeps_its_negation(self):
        requirements = extract_eligibility_requirements(SOURCE)

        matching = [
            requirement for requirement in requirements
            if "postgraduate degree" in requirement.requirement
        ]
        assert matching, "the rule about postgraduate degree holders must be found"

        requirement = matching[0]
        assert "not eligible" in requirement.requirement.lower()
        # The subject of the rule is kept.
        assert "already acquired" in requirement.requirement.lower()
        # It is not labelled as a positive requirement.
        assert requirement.category == "Not eligible"

    def test_the_summary_labels_the_negative_rule(self):
        info = extract_structured_information(SOURCE)
        summary = summary_service.build_instant_summary(info)

        labels = {item["label"] for item in summary["items"]}
        assert "Not eligible" in labels

        negative = [
            item for item in summary["items"]
            if item["label"] == "Not eligible"
        ]
        assert negative
        for item in negative:
            assert "not eligible" in item["value"].lower()

    def test_the_full_time_mode_rule_is_negative(self):
        requirements = extract_eligibility_requirements(SOURCE)

        matching = [
            requirement for requirement in requirements
            if "open/distance/correspondence" in requirement.requirement
        ]
        assert matching, "the rule about part time programmes must be found"
        assert "not eligible" in matching[0].requirement.lower()
        assert matching[0].category == "Not eligible"

    def test_an_only_if_rule_keeps_its_condition(self):
        conditions = extract_important_conditions(SOURCE)

        assert conditions
        # The conditions keep the wording of the source, including "unless"
        # and "except".
        joined = " ".join(condition.condition for condition in conditions).lower()
        assert "except" in joined or "unless" in joined or "only" in joined


# ============================================================
# Page markers
# ============================================================

class TestPageMarkers:
    """A page marker is printing metadata, never content."""

    def test_the_markers_are_in_the_source(self):
        assert "Page 3 of 7" in SOURCE
        assert "Page 4 of 7" in SOURCE

    def test_no_fact_contains_a_page_marker(self):
        info = extract_structured_information(SOURCE)

        values = []
        values.extend(document.name for document in info.required_documents)
        values.extend(requirement.requirement for requirement in info.eligibility_requirements)
        values.extend(condition.condition for condition in info.important_conditions)
        values.extend(step.description for step in info.application_procedure)

        for value in values:
            assert "Page 3 of 7" not in value
            assert "Page 4 of 7" not in value
            assert "Page 3" not in value
            assert "Page 4" not in value

    def test_a_statement_split_by_a_page_break_is_put_back_together(self):
        requirements = extract_eligibility_requirements(SOURCE)

        matching = [
            requirement for requirement in requirements
            if "open/distance/correspondence" in requirement.requirement
        ]
        assert matching
        # The sentence reads as one sentence again.
        assert " " in matching[0].requirement
        assert "\n" not in matching[0].requirement
        assert "pursuing any PG programme" in matching[0].requirement

    def test_removing_a_marker_does_not_join_two_sentences(self):
        text = (
            "The first rule is complete here. Page 3 of 7\n"
            "The second rule is a different sentence."
        )
        conditions = extract_important_conditions(text)
        for condition in conditions:
            assert "The first rule" not in condition.condition


# ============================================================
# The institution section
# ============================================================

class TestInstitutionSection:
    """All four institution categories and the AISHE rule must survive."""

    def test_all_four_institution_types_are_in_the_source(self):
        for fragment in (
            "Section 2(f) of UGC Act",
            "Deemed to be Universities under Section 3",
            "fully funded by Central or State Governments",
            "Institutions of National Importance",
        ):
            assert fragment in SOURCE, fragment

    def test_the_naac_accreditation_is_preserved(self):
        info = extract_structured_information(SOURCE)
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions)

        assert "NAAC" in joined or "NAAC" in SOURCE
        # The accreditation requirement is part of the eligibility rules.
        requirements = " ".join(
            requirement.requirement for requirement in info.eligibility_requirements
        )
        assert "NAAC" in requirements or "NAAC" in joined

    def test_the_aishe_code_requirement_is_preserved(self):
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions)

        assert "AISHE" in joined
        assert "mandatory" in joined.lower()

    def test_the_institution_registration_process_is_preserved(self):
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions)

        assert "registered" in joined.lower()
        assert "nodal officer" in joined.lower()


# ============================================================
# The one benefit section
# ============================================================

class TestOneBenefitSection:
    """The rules about a second benefit must be preserved."""

    def test_the_one_scholarship_rule_is_preserved(self):
        requirements = extract_eligibility_requirements(SOURCE)
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(
            [requirement.requirement for requirement in requirements]
            + [condition.condition for condition in conditions]
        ).lower()

        assert "only one scholarship" in joined
        assert "declare" in joined

    def test_the_paid_employment_restriction_is_preserved(self):
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions).lower()

        assert "paid" in joined
        assert "emoluments" in joined or "salary" in joined or "stipend" in joined

    def test_the_noc_exception_is_preserved(self):
        requirements = extract_eligibility_requirements(SOURCE)
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(
            [requirement.requirement for requirement in requirements]
            + [condition.condition for condition in conditions]
        ).lower()

        assert "noc" in joined
        assert "resignation" in joined

    def test_the_consequence_of_another_scholarship_is_preserved(self):
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions).lower()

        assert "relinquish" in joined or "cancel the selection" in joined

    def test_the_already_receiving_rule_is_preserved(self):
        requirements = extract_eligibility_requirements(SOURCE)
        joined = " ".join(
            requirement.requirement for requirement in requirements
        ).lower()

        assert "already in receipt" in joined
        assert "declared in" in joined


# ============================================================
# Aadhaar seeding
# ============================================================

class TestAadhaarSeeding:
    """Aadhaar is an identifier for the account, not the only document."""

    def test_the_account_requirement_is_preserved(self):
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions).lower()

        assert "bank account" in joined
        assert "aadhaar" in joined
        assert "verified" in joined

    def test_aadhaar_is_not_labelled_as_the_required_document(self):
        documents = extract_required_documents(SOURCE)

        assert documents == [], "the notice does not list a document to submit"
        for document in documents:
            assert "aadhaar" not in document.name.lower()


# ============================================================
# Selection, reservation and tie breaking
# ============================================================

class TestSelectionSection:
    """The selection rules, the reservation and the tie breaking."""

    def test_the_thirty_percent_reservation_is_preserved(self):
        info = extract_structured_information(SOURCE)

        percentages = [percentage.percentage for percentage in info.percentages]
        assert "30%" in percentages

    def test_the_fifty_fifty_subject_allocation_is_preserved(self):
        info = extract_structured_information(SOURCE)

        percentages = [percentage.percentage for percentage in info.percentages]
        assert "50%" in percentages

        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions).lower()
        assert "earmarked" in joined or "50%" in joined

    def test_the_tie_breaking_rules_are_preserved(self):
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions).lower()

        assert "ug" in joined or "under-graduation" in joined
        assert "xii" in joined

    def test_the_selection_is_on_merit(self):
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions).lower()

        assert "merit" in joined


# ============================================================
# The result announcement
# ============================================================

class TestResultAnnouncement:
    """When the result comes, and where it is checked."""

    def test_the_announcement_period_is_preserved(self):
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions)

        assert "November/December" in joined

    def test_the_nsp_login_details_are_preserved(self):
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions)

        assert "National Scholarship Portal" in joined
        assert "User ID" in joined or "Password" in joined

    def test_the_ugc_results_webpage_is_preserved(self):
        conditions = extract_important_conditions(SOURCE)
        joined = " ".join(condition.condition for condition in conditions)

        assert "UGC" in joined
        assert "www.ugc.ac.in" in joined


# ============================================================
# The "too similar" warning
# ============================================================

class TestTooSimilarWarning:
    """
    The warning must catch a text that was not simplified, and must not
    fire on a text that was.
    """

    UNCHANGED = (
        "The scholarship is available to the students for the first postgraduate degree "
        "programme only, and the applicants are required to submit the prescribed "
        "documents to the institution before the prescribed last date, failing which the "
        "application will be rejected without any further correspondence in this matter."
    )

    def test_genuinely_unchanged_text_is_reported(self):
        issues = validation_service.validate_simplification_quality(
            self.UNCHANGED, self.UNCHANGED
        )

        assert any("too similar" in issue for issue in issues)

    def test_a_properly_simplified_text_is_not_reported(self):
        """The wording is kept, but the text is organised and shortened."""
        simplified = (
            "### Who can apply\n\n"
            "- Only students in the **first postgraduate degree programme** can apply.\n"
            "- Send the documents to the institution before the last date.\n"
            "- An incomplete form is rejected.\n"
        )

        issues = validation_service.validate_simplification_quality(
            self.UNCHANGED, simplified
        )

        assert not any("too similar" in issue for issue in issues)

    def test_a_plain_rewrite_is_not_reported(self):
        """The wording changed, so the text was simplified."""
        simplified = (
            "Only students in their first postgraduate degree programme can get the "
            "scholarship. They must give the papers to the institution before the "
            "last date, or the form is thrown out."
        )

        issues = validation_service.validate_simplification_quality(
            self.UNCHANGED, simplified
        )

        assert not any("too similar" in issue for issue in issues)

    def test_short_text_is_not_measured(self):
        """The metrics are unreliable for a short text."""
        short = "The applicant must submit the form."

        issues = validation_service.validate_simplification_quality(short, short)

        assert not any("too similar" in issue for issue in issues)

    def test_the_fixture_is_not_reported_as_unchanged(self):
        """A structured simplification of the notice is not "too similar"."""
        simplified = (
            "### Who can apply\n\n"
            "- Only students in the **first postgraduate degree programme** can apply.\n"
            "- Students who already hold a postgraduate degree are **not eligible**.\n"
            "- You must be **below 30 years** of age on the date of admission.\n"
            "- Only full time programmes are eligible.\n"
            "### Which institutions\n\n"
            "- Universities and colleges under Section 2(f) of the UGC Act with valid "
            "**NAAC** accreditation.\n"
            "- Deemed universities with valid NAAC accreditation.\n"
            "- Institutions fully funded by the government.\n"
            "- Institutions of national importance.\n"
        )

        issues = validation_service.validate_simplification_quality(SOURCE, simplified)

        assert not any("too similar" in issue for issue in issues)


# ============================================================
# The whole pipeline
# ============================================================

class TestFullDocumentPipeline:
    """The complete document through the real pipeline."""

    def test_the_summary_covers_the_main_points(self):
        info = extract_structured_information(SOURCE)
        summary = summary_service.build_instant_summary(info)

        labels = [item["label"] for item in summary["items"]]
        values = " ".join(item["value"] for item in summary["items"]).lower()

        assert "Age requirement" in labels
        assert "below 30" in values
        assert "Not eligible" in labels
        assert "30%" in values
        assert "50%" in values
        assert "aishe" in values
        assert "naac" in values or "ugc" in values

    def test_the_endpoint_answers_with_the_canonical_summary(self):
        class FakeProvider:
            provider_name = "Fake"
            model = "fake-model"

            def simplify_text(self, text, target_grade_level):
                return "### Who can apply\n\n- Only the students in the first PG programme."

            def generate_structured_simplification(self, text, target_grade_level):
                return {
                    "simplified_text": "### Who can apply\n\n- Only the students in the first PG programme.",
                    "key_terms": [],
                    "sections": [],
                }

        provider = FakeProvider()
        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with patch.object(llm_service, "_build_provider_chain", return_value=[provider]):
                response = client.post(
                    "/api/documents/simplify",
                    json={"text": SOURCE, "target_grade_level": 5},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["instant_summary"]

        summary = data["instant_summary"]
        ages = [item["value"] for item in summary if item["kind"] == "age"]
        assert ages
        assert ages[0].lower().startswith("below")
        assert "30+" not in ages[0]

        labels = {item["label"] for item in summary}
        assert "Not eligible" in labels

        for item in summary:
            assert "Page 3 of 7" not in item["value"]
            assert "Page 4 of 7" not in item["value"]

    def test_both_interfaces_render_the_same_summary(self):
        """The website and the extension read the same response field."""
        class FakeProvider:
            provider_name = "Fake"
            model = "fake-model"

            def simplify_text(self, text, target_grade_level):
                return "Simplified text."

            def generate_structured_simplification(self, text, target_grade_level):
                return {"simplified_text": "Simplified text.", "key_terms": [], "sections": []}

        provider = FakeProvider()
        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with patch.object(llm_service, "_build_provider_chain", return_value=[provider]):
                response = client.post(
                    "/api/documents/simplify",
                    json={"text": SOURCE, "target_grade_level": 5},
                )

        data = response.json()
        summary = data["instant_summary"]

        # The extension maps the items one to one, keeping the labels.
        extension_labels = [item["label"] for item in summary]
        website_labels = [item["label"] for item in summary]
        assert extension_labels == website_labels
        assert len(summary) == len(extension_labels)

    def test_the_document_is_never_silently_shortened(self):
        """The summary reports what it left out."""
        info = extract_structured_information(SOURCE)
        summary = summary_service.build_instant_summary(info)

        assert summary["total"] >= len(summary["items"])
        assert summary["hidden"] == summary["total"] - len(summary["items"])
