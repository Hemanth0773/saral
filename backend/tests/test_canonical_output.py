"""
Regression tests for the canonical simplified output.

The website and the Chrome extension must show the same result for the same
input, so the backend produces one canonical result: the simplified text, the
Instant Summary and the validation warnings. These tests pin that contract
down with deterministic fixtures - no live model is called.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import llm_service, summary_service
from app.services.extraction_service import extract_structured_information

client = TestClient(app)


# ============================================================
# Fixtures
# ============================================================

SCHOLARSHIP_ELIGIBILITY = """CENTRAL SCHOLARSHIP SCHEME FOR THE ACADEMIC YEAR 2026-27

1. ELIGIBILITY

The scholarship is open to students who are enrolled in a recognised university/college/institute in India and who have secured at least 60% marks in their last qualifying examination. The applicant must be under 30 years of age as on 31 July 2026. The annual family income of the applicant must not exceed Rs. 2,50,000.

The applicant must not be in receipt of any other benefit under a scheme of the Central Government. 25% of the scholarships are reserved for female candidates.

2. SCHOLARSHIP AMOUNT

The scholarship amount is Rs. 2,50,000 per annum and is paid in two instalments on the National e-Scholarship Portal, normally announced in November/December.

3. TERMS AND CONDITIONS

Except in the case of a medical emergency, the applicant must not change the bank account after the application is submitted. The institution shall verify the information submitted by the student before uploading the same on the portal. The institution shall retain the documents for verification for a period of five years from the date of upload.

4. SELECTION

Selection shall be made on the basis of merit. In case of a tie, the candidate with the higher score in the qualifying examination shall be preferred.

Page 4 of 7
"""

SCHOLARSHIP_PROCEDURE = """3. PROCEDURE FOR AVAILING THE SCHOLARSHIP

I. Students are required to apply annually through the National e-Scholarship Portal. The portal shall remain open for applications as notified by the Commission each year.

II. Incomplete applications will be rejected. The applicant must complete every mandatory field before the final submission, otherwise the form will not be accepted by the portal.

III. The students shall submit the required documents to their institutions to enable, match of name of student, bank account number, and the institution shall upload the same on the portal on behalf of the student.

IV. The bank account of the student must be KYC-compliant. The account must be in the name of the student and must be linked with Aadhaar for the direct benefit transfer.

V. The applicant must provide correct bank details. Any wrong information furnished by the applicant, as per requirement of scheme, will be the sole responsibility of the student.

VI. The institution shall verify the information submitted by the student before uploading the same on the portal.

VII. The institution shall retain the documents for verification for a period of five years from the date of upload. The institution shall produce the documents on demand as and when required by the Commission.

VIII. The University Grants Commission may ask for the documents from the institution for verification at any time and the institution shall comply with such a request without delay.

IX. The student shall upload scanned copies of the certificates along with the application. The documents must be legible and in the prescribed format.

Page 5 of 7
"""

SHORT_PARAGRAPH = (
    "Applicants must submit their application before 31 December 2026. "
    "The application must include the Aadhaar card and the income certificate."
)

TWO_GROUPS = """INSTRUCTIONS FOR STUDENTS AND INSTITUTIONS

Students must apply through the portal before the deadline. Students must upload the scanned certificates themselves.

Institutions must verify the documents before uploading them on the portal. Institutions must retain the documents for five years.

Page 2 of 4
"""


class FakeProvider:
    """A provider that returns a fixed simplified text."""

    provider_name = "Fake"

    def __init__(self, simplified_text):
        self.simplified_text = simplified_text
        self.model = "fake-model"
        self.calls = []

    def simplify_text(self, text, target_grade_level):
        self.calls.append(text)
        return self.simplified_text

    def generate_structured_simplification(self, text, target_grade_level):
        self.calls.append(text)
        return {
            "simplified_text": self.simplified_text,
            "key_terms": [],
            "sections": [],
        }


def run_simplify(text, simplified_text="Simplified text"):
    """Runs the simplify endpoint with a deterministic provider."""
    provider = FakeProvider(simplified_text)
    with patch.object(llm_service, "get_llm_provider", return_value=provider):
        with patch.object(llm_service, "_build_provider_chain", return_value=[provider]):
            response = client.post(
                "/api/documents/simplify",
                json={"text": text, "target_grade_level": 5},
            )
    return response, provider


# ============================================================
# One canonical result
# ============================================================

class TestCanonicalResult:
    """The same input produces the same result for every interface."""

    def test_the_endpoint_returns_the_instant_summary(self):
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY)
        assert response.status_code == 200
        data = response.json()

        assert "instant_summary" in data
        assert data["instant_summary"], "the summary must not be empty for a notice with facts"
        for item in data["instant_summary"]:
            assert set(item) == {"id", "kind", "label", "value", "severity"}

    def test_the_summary_counts_are_reported(self):
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY)
        data = response.json()

        assert data["metadata"]["summary_total"] == len(data["instant_summary"]) + data["metadata"]["summary_hidden"]

    def test_two_requests_for_the_same_input_return_the_same_summary(self):
        first, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY)
        second, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY)

        assert first.json()["instant_summary"] == second.json()["instant_summary"]

    def test_the_summary_is_built_from_the_source_not_from_the_model(self):
        """The model output is never used to build the summary."""
        response, _ = run_simplify(
            SCHOLARSHIP_ELIGIBILITY,
            simplified_text="The model said something completely different.",
        )
        data = response.json()

        values = " ".join(item["value"] for item in data["instant_summary"])
        assert "completely different" not in values
        assert "2,50,000" in values


# ============================================================
# Summary quality
# ============================================================

class TestSummaryQuality:
    """The summary holds complete, trustworthy facts."""

    def test_labels_are_not_duplicated(self):
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY)
        for item in response.json()["instant_summary"]:
            assert not item["value"].lower().startswith(f"{item['label'].lower()}:")

    def test_page_markers_are_never_facts(self):
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY)
        for item in response.json()["instant_summary"]:
            assert "page 4 of 7" not in item["value"].lower()

    def test_section_headings_are_never_facts(self):
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY)
        for item in response.json()["instant_summary"]:
            assert "eligibility" != item["value"].strip().lower()
            assert "terms and conditions" != item["value"].strip().lower()

    def test_fragments_are_never_facts(self):
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY)
        for item in response.json()["instant_summary"]:
            assert not item["value"].startswith(",")
            assert len(item["value"]) >= 4

    def test_the_age_rule_keeps_its_direction(self):
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY)
        ages = [
            item["value"] for item in response.json()["instant_summary"]
            if item["kind"] == "age"
        ]

        assert ages, "the age rule must be reported"
        assert "under 30" in ages[0]
        assert "30+" not in ages[0]

    def test_the_amount_is_reported(self):
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY)
        values = " ".join(item["value"] for item in response.json()["instant_summary"])

        assert "2,50,000" in values

    def test_the_same_fact_is_not_shown_twice(self):
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY)
        values = [item["value"] for item in response.json()["instant_summary"]]

        assert len(values) == len(set(values))


# ============================================================
# The procedure notice
# ============================================================

class TestProcedureNotice:
    """The nine clauses of the procedure are the key steps of the document."""

    def test_the_steps_are_reported(self):
        response, _ = run_simplify(SCHOLARSHIP_PROCEDURE)
        steps = [
            item for item in response.json()["instant_summary"]
            if item["kind"] == "procedure"
        ]

        assert steps
        assert steps[0]["label"].startswith("Step")

    def test_the_heading_is_not_a_step(self):
        response, _ = run_simplify(SCHOLARSHIP_PROCEDURE)
        for item in response.json()["instant_summary"]:
            assert "PROCEDURE FOR AVAILING" not in item["value"].upper()

    def test_student_and_institution_instructions_stay_apart(self):
        response, _ = run_simplify(TWO_GROUPS)
        values = " ".join(item["value"] for item in response.json()["instant_summary"])

        assert "Students must apply" in values or "Students must upload" in values
        assert "Institutions must verify" in values or "Institutions must retain" in values


# ============================================================
# Long documents and chunking
# ============================================================

class TestLongDocuments:
    """A long document is chunked and combined in order."""

    def test_the_chunks_are_combined_in_order(self):
        long_text = "\n\n".join(
            f"Paragraph {index}. The applicant must submit the form number {index}."
            for index in range(60)
        )
        provider = FakeProvider("Simplified paragraph.")
        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with patch.object(llm_service, "_build_provider_chain", return_value=[provider]):
                response = client.post(
                    "/api/documents/simplify",
                    json={"text": long_text, "target_grade_level": 5},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["chunks"] > 1
        # Every chunk produced one piece of text, in order.
        assert data["simplified_text"].count("Simplified paragraph.") == data["metadata"]["chunks"]

    def test_a_chunk_is_not_truncated_at_a_clause_boundary(self):
        long_text = "\n\n".join(
            f"Clause {index}. The applicant must submit the documents for year {index}."
            for index in range(50)
        )
        provider = FakeProvider("The applicant must submit the documents for the year.")
        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with patch.object(llm_service, "_build_provider_chain", return_value=[provider]):
                response = client.post(
                    "/api/documents/simplify",
                    json={"text": long_text, "target_grade_level": 5},
                )

        data = response.json()
        for piece in data["simplified_text"].split("\n\n"):
            assert piece.strip().endswith("."), "a chunk must not end mid clause"


# ============================================================
# Broken model output
# ============================================================

class TestBrokenModelOutput:
    """Broken output is reported, never presented as a good result."""

    def test_an_empty_model_answer_is_a_failure(self):
        class EmptyProvider(FakeProvider):
            def simplify_text(self, text, target_grade_level):
                raise llm_service.LLMServiceError("Provider returned an empty completion.")

            def generate_structured_simplification(self, text, target_grade_level):
                raise llm_service.LLMServiceError("Provider returned an empty completion.")

        provider = EmptyProvider("")
        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with patch.object(llm_service, "_build_provider_chain", return_value=[provider]):
                with patch.object(settings, "LLM_MAX_RETRIES", 1):
                    response = client.post(
                        "/api/documents/simplify",
                        json={"text": SHORT_PARAGRAPH, "target_grade_level": 5},
                    )

        assert response.status_code >= 400
        assert response.json()["success"] is False

    def test_a_truncated_answer_is_reported_by_the_validation(self):
        truncated = "The applicant must have at least 60 % marks in their last"
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY, simplified_text=truncated)
        data = response.json()

        assert data["validation_passed"] is False
        assert data["validation_failures"]

    def test_a_missing_fact_is_reported(self):
        response, _ = run_simplify(
            SCHOLARSHIP_ELIGIBILITY,
            simplified_text="Students must apply every year. The portal is open in November.",
        )
        data = response.json()

        assert data["validation_passed"] is False
        failures = " ".join(data["validation_failures"])
        assert "not preserved" in failures


# ============================================================
# Markdown
# ============================================================

class TestMarkdownIsPassedThrough:
    """The backend does not rewrite the Markdown the model produced."""

    def test_markdown_is_kept_verbatim(self):
        markdown = (
            "### 1. ELIGIBILITY\n\n"
            "- The student must have **60% marks**.\n"
            "- The portal is open \\*annually\\*.\n"
        )
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY, simplified_text=markdown)

        assert response.json()["simplified_text"] == markdown

    def test_malicious_html_is_not_executed_or_altered(self):
        markdown = "<script>alert(1)</script>\n\n**safe**"
        response, _ = run_simplify(SCHOLARSHIP_ELIGIBILITY, simplified_text=markdown)

        # The text is returned unchanged; the interfaces render it as text.
        assert response.json()["simplified_text"] == markdown


# ============================================================
# The summary builder on its own
# ============================================================

class TestSummaryBuilder:
    """Unit tests for the canonical summary builder."""

    def test_an_empty_document_produces_an_empty_summary(self):
        result = summary_service.build_instant_summary(None)
        assert result["items"] == []
        assert result["total"] == 0

    def test_the_summary_is_capped(self):
        info = extract_structured_information(SCHOLARSHIP_PROCEDURE)
        result = summary_service.build_instant_summary(info, None, limit=3)

        assert len(result["items"]) <= 3
        assert result["total"] >= len(result["items"])

    def test_the_procedure_steps_are_capped(self):
        info = extract_structured_information(SCHOLARSHIP_PROCEDURE)
        result = summary_service.build_instant_summary(info, None)

        steps = [item for item in result["items"] if item["kind"] == "procedure"]
        assert len(steps) <= summary_service.MAX_PROCEDURE_STEPS

    def test_the_steps_that_did_not_fit_are_counted_as_hidden(self):
        """The interface must be able to say that more facts were found."""
        info = extract_structured_information(SCHOLARSHIP_PROCEDURE)
        result = summary_service.build_instant_summary(info, None)

        assert result["total"] > len(result["items"])
        assert result["hidden"] == result["total"] - len(result["items"])
