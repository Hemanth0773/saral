"""
Regression tests for unsupported facts in simplified government documents.

The source is a scholarship notice, the reported simplified output is the
one that introduced "You must declare on Page 4 of 7 of your application",
turned "university/college/institute" into "school" and turned "normally
announced" into a promise.
"""

import re
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.services import llm_service, text_fidelity, validation_service


# ============================================================
# Source and (incorrect) simplified text
# ============================================================

SCHOLARSHIP_NOTICE = """Government of India
Ministry of Education
National Scholarship Portal

SCHOLARSHIP GUIDELINES FOR THE ACADEMIC YEAR 2026-27

1. The scholarship is open to students who are enrolled in a recognised university/college/institute and who have secured at least 60% marks in their last qualifying examination.

2. The annual family income of the applicant must not exceed Rs. 2,50,000 per annum. For students in the final year of a professional course, the income of the guardian will be considered.

3. If the student is already in receipt of any scholarship/fellowship, he/she is still eligible to apply under the scheme subject to the condition that it is declared in his/her application.

4. The selection committee will shortlist the applications received. The list of shortlisted candidates will be normally announced in November/December on the National Scholarship Portal.

5. The applicant must upload a scanned copy of the marksheet, the bank passbook and the income certificate. The institution must verify the documents before the final submission is made.

6. The applicant must not be in receipt of any other benefit under a scheme of the Central Government.

Page 4 of 7
"""

# The reported incorrect output.
BAD_SIMPLIFIED = """You can apply if you are studying at a school and you got at least 60% marks. Your family income must not be more than Rs. 2,50,000. You must declare on Page 4 of 7 of your application if you already get a scholarship or fellowship. The list of shortlisted candidates will be announced in November/December on the portal. You must upload a scanned copy of the marksheet, the bank passbook and the income certificate. The institution must verify the documents.
"""

# A simplification that keeps the meaning of the source.
GOOD_SIMPLIFIED = """You can apply if you are studying at a university, college or institute and you got at least 60% marks. Your family income must not be more than Rs. 2,50,000. If you already get a scholarship or fellowship, you can still apply, but you must declare it in your application. The list of shortlisted candidates will normally be announced in November/December on the National Scholarship Portal. You must upload a scanned copy of the marksheet, the bank passbook and the income certificate. The institution must verify the documents.
"""


# ============================================================
# Artifact stripping
# ============================================================

class TestDocumentArtifacts:
    """Pagination artifacts must not reach the model"""

    def test_standalone_page_marker_is_removed(self):
        cleaned, artifacts = text_fidelity.strip_document_artifacts(SCHOLARSHIP_NOTICE)

        assert "Page 4 of 7" not in cleaned
        assert artifacts == ["Page 4 of 7"]
        # The rest of the notice survives untouched.
        assert "university/college/institute" in cleaned
        assert "Rs. 2,50,000" in cleaned

    def test_backend_page_marker_is_removed(self):
        source = "First line.\n--- Page 3 (text) ---\nSecond line."
        cleaned, artifacts = text_fidelity.strip_document_artifacts(source)

        assert "--- Page 3 (text) ---" not in cleaned
        assert artifacts == ["--- Page 3 (text) ---"]
        assert "First line." in cleaned and "Second line." in cleaned

    def test_a_sentence_that_mentions_a_page_is_kept(self):
        source = "The fee details are given on page 4 of the notification."
        cleaned, artifacts = text_fidelity.strip_document_artifacts(source)

        assert cleaned == source
        assert artifacts == []

    def test_ocr_artifacts_are_removed(self):
        source = "Body text.\n--- SCANNED PAGES (OCR) ---\nMore body text."
        cleaned, artifacts = text_fidelity.strip_document_artifacts(source)

        assert "SCANNED PAGES" not in cleaned
        assert len(artifacts) == 1

    def test_the_model_receives_text_without_page_markers(self):
        """The pipeline must send the cleaned text to the provider."""
        sent = {}

        class RecordingProvider:
            provider_name = "Recording"
            model = "recording-model"

            def simplify_text(self, text, target_grade_level):
                sent["text"] = text
                return "simplified"

            def generate_structured_simplification(self, text, target_grade_level):
                sent["text"] = text
                return {"simplified_text": "simplified", "key_terms": [], "sections": []}

        provider = RecordingProvider()
        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with patch.object(llm_service, "_build_provider_chain", return_value=[provider]):
                llm_service.generate_simplification_response(
                    SCHOLARSHIP_NOTICE, 5, "doc_scholarship"
                )

        assert "Page 4 of 7" not in sent["text"]
        # The original text is still reported unchanged in the response.
        assert "Page 4 of 7" in SCHOLARSHIP_NOTICE


# ============================================================
# Page references
# ============================================================

class TestPageReferenceDetection:
    """A page marker must never become an instruction"""

    def test_page_marker_turned_into_an_instruction_is_detected(self):
        issues = text_fidelity.detect_page_reference_issues(
            SCHOLARSHIP_NOTICE, BAD_SIMPLIFIED
        )

        assert issues, "the page marker turned into content must be reported"
        assert any("Page 4 of 7" in issue for issue in issues)
        assert any("turned into content" in issue for issue in issues)

    def test_a_faithful_simplification_raises_no_page_issue(self):
        issues = text_fidelity.detect_page_reference_issues(
            SCHOLARSHIP_NOTICE, GOOD_SIMPLIFIED
        )

        assert issues == []

    def test_a_page_reference_that_the_source_never_mentions_is_detected(self):
        source = "The applicant must submit the fee receipt."
        simplified = "You must submit the fee receipt on Page 9 of 12."

        issues = text_fidelity.detect_page_reference_issues(source, simplified)

        assert any("Unsupported page reference" in issue for issue in issues)

    def test_a_page_reference_kept_as_a_plain_mention_is_allowed(self):
        source = "The fee details are given on page 4 of the notification."
        simplified = "The fee details are on page 4 of the notification."

        issues = text_fidelity.detect_page_reference_issues(source, simplified)

        assert issues == []

    def test_a_page_reference_present_in_the_body_is_not_reported_as_new(self):
        """The same page number on a footer line and inside a sentence is fine."""
        source = "The fee details are given on page 4 of the notification.\n\nPage 4 of 7"
        simplified = "The fee details are on page 4 of the notification."

        issues = text_fidelity.detect_page_reference_issues(source, simplified)

        assert issues == []

    def test_a_page_reference_turned_into_an_instruction_is_detected_inline(self):
        source = "The fee details are given on page 4 of the notification."
        simplified = "You must write the fee details on page 4 of the notification."

        issues = text_fidelity.detect_page_reference_issues(source, simplified)

        assert any("turned into an instruction" in issue for issue in issues)


# ============================================================
# Certainty
# ============================================================

class TestCertaintyPreservation:
    """"normally" must not become a promise"""

    def test_dropping_normally_is_detected(self):
        issues = text_fidelity.detect_certainty_issues(SCHOLARSHIP_NOTICE, BAD_SIMPLIFIED)

        assert issues, "the dropped certainty qualifier must be reported"
        assert any("normally" in issue for issue in issues)
        assert any("will" in issue for issue in issues)

    def test_keeping_normally_raises_no_issue(self):
        issues = text_fidelity.detect_certainty_issues(SCHOLARSHIP_NOTICE, GOOD_SIMPLIFIED)

        assert issues == []

    def test_an_equivalent_hedge_is_accepted(self):
        source = "The results are normally announced in November."
        simplified = "The results are usually announced in November."

        issues = text_fidelity.detect_certainty_issues(source, simplified)

        assert issues == []

    def test_a_dropped_condition_is_detected(self):
        source = "You may apply subject to the condition that you declare it."
        simplified = "You may apply. You have to declare it."

        issues = text_fidelity.detect_certainty_issues(source, simplified)

        assert any("Condition or exception" in issue for issue in issues)

    def test_a_condition_written_differently_is_accepted(self):
        source = "You may apply subject to the condition that you declare it."
        simplified = "If you already have one, you can still apply, but you must declare it."

        issues = text_fidelity.detect_certainty_issues(source, simplified)

        assert issues == []


# ============================================================
# Entity substitution
# ============================================================

class TestEntitySubstitution:
    """A university must not become a school"""

    def test_university_turned_into_school_is_detected(self):
        issues = text_fidelity.detect_entity_issues(SCHOLARSHIP_NOTICE, BAD_SIMPLIFIED)

        assert issues, "the swapped entity must be reported"
        assert any("university" in issue and "school" in issue for issue in issues)

    def test_keeping_the_original_entity_raises_no_issue(self):
        issues = text_fidelity.detect_entity_issues(SCHOLARSHIP_NOTICE, GOOD_SIMPLIFIED)

        assert issues == []

    def test_summarising_away_one_term_is_not_a_substitution(self):
        source = "The college and the university both verified the documents."
        simplified = "The college verified the documents."

        issues = text_fidelity.detect_entity_issues(source, simplified)

        assert issues == []

    def test_a_ministry_turned_into_a_board_is_detected(self):
        source = "The Ministry of Education published the notification."
        simplified = "The board published the notification."

        issues = text_fidelity.detect_entity_issues(source, simplified)

        assert any("ministry" in issue and "board" in issue for issue in issues)


# ============================================================
# Unsupported numbers in obligations
# ============================================================

class TestUnsupportedNumbers:
    """An obligation must not quote a number the source never states"""

    def test_invented_numbers_in_an_obligation_are_detected(self):
        issues = text_fidelity.detect_unsupported_number_issues(
            SCHOLARSHIP_NOTICE, BAD_SIMPLIFIED
        )

        assert issues, "the invented page numbers must be reported"
        assert any("4" in issue for issue in issues)

    def test_a_faithful_simplification_raises_no_issue(self):
        issues = text_fidelity.detect_unsupported_number_issues(
            SCHOLARSHIP_NOTICE, GOOD_SIMPLIFIED
        )

        assert issues == []

    def test_a_number_from_the_source_is_accepted(self):
        source = "The applicant must submit the receipt of Rs. 2,50,000."
        simplified = "You must submit the receipt of Rs. 2,50,000."

        issues = text_fidelity.detect_unsupported_number_issues(source, simplified)

        assert issues == []


# ============================================================
# End to end validation
# ============================================================

class TestFinalResponseValidation:
    """The pipeline must report the problem instead of passing silently"""

    def _response(self, simplified_text):
        return {
            "original_text": SCHOLARSHIP_NOTICE,
            "simplified_text": simplified_text,
            "metadata": {},
        }

    def test_the_reported_output_does_not_pass_validation(self):
        validated = validation_service.validate_final_response(
            self._response(BAD_SIMPLIFIED)
        )

        assert validated["validation_passed"] is False
        failures = " ".join(validated["validation_failures"])
        assert "Page 4 of 7" in failures
        assert "normally" in failures
        assert "university" in failures and "school" in failures

    def test_a_faithful_simplification_passes_validation(self):
        validated = validation_service.validate_final_response(
            self._response(GOOD_SIMPLIFIED)
        )

        assert validated["validation_passed"] is True
        assert validated["validation_failures"] == []

    def test_the_endpoint_reports_the_failure(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        class EchoProvider:
            provider_name = "Echo"
            model = "echo-model"

            def simplify_text(self, text, target_grade_level):
                return BAD_SIMPLIFIED

            def generate_structured_simplification(self, text, target_grade_level):
                return {
                    "simplified_text": BAD_SIMPLIFIED,
                    "key_terms": [],
                    "sections": [],
                }

        provider = EchoProvider()
        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with patch.object(llm_service, "_build_provider_chain", return_value=[provider]):
                response = client.post(
                    "/api/documents/simplify",
                    json={"text": SCHOLARSHIP_NOTICE, "target_grade_level": 5},
                )

        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["validation_passed"] is False
        assert data["validation_failures"]
        assert "simplified_text" in data


# ============================================================
# Prompt instructions
# ============================================================

class TestPromptInstructions:
    """The model has to be told about artifacts, qualifiers and entities"""

    def _prompt(self):
        provider = llm_service.LLMProvider.__new__(llm_service.LLMProvider)
        return provider._get_system_prompt()

    def test_the_system_prompt_covers_page_artifacts(self):
        prompt = self._prompt()
        assert "Page 4 of 7" in prompt
        assert "artifacts" in prompt.lower()

    def test_the_system_prompt_covers_certainty(self):
        prompt = self._prompt().lower()
        assert "normally" in prompt
        assert "subject to" in prompt

    def test_the_system_prompt_covers_entity_types(self):
        prompt = self._prompt().lower()
        assert "university" in prompt
        assert "school" in prompt

    def test_the_user_prompt_warns_about_artifacts(self):
        provider = llm_service.LLMProvider.__new__(llm_service.LLMProvider)
        prompt = provider._build_simplification_prompt("some text", 5)
        assert "DOCUMENT ARTIFACTS" in prompt
        assert "Page 4 of 7" in prompt

    def test_the_structured_prompt_warns_about_artifacts(self):
        provider = llm_service.LLMProvider.__new__(llm_service.LLMProvider)
        prompt = provider._build_structured_simplification_prompt("some text", 5)
        assert "DOCUMENT ARTIFACTS" in prompt
