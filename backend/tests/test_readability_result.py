"""
Tests for the measured readability of the simplified document.

The grade has to be measured for real documents, has to say honestly when the
target was not reached, and has to be left out completely when it cannot be
measured.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import llm_service, readability_service

client = TestClient(app)

SOURCE = """The scholarship is available to the students for the first postgraduate degree
programme only. The applicant must submit the prescribed documents to the
institution before the prescribed last date, failing which the application will
be rejected without any further correspondence in this matter.
"""

SIMPLIFIED = """Only students in their first postgraduate degree programme can get the scholarship.

Send the documents to the institution before the last date. An incomplete form is thrown out.
"""


class FakeProvider:
    provider_name = "Fake"
    model = "fake-model"

    def simplify_text(self, text, target_grade_level):
        return SIMPLIFIED

    def generate_structured_simplification(self, text, target_grade_level):
        return {"simplified_text": SIMPLIFIED, "key_terms": [], "sections": []}


def run_simplify():
    provider = FakeProvider()
    with patch.object(llm_service, "get_llm_provider", return_value=provider):
        with patch.object(llm_service, "_build_provider_chain", return_value=[provider]):
            return client.post(
                "/api/documents/simplify",
                json={"text": SOURCE, "target_grade_level": 5},
            )


class TestReadabilityMeasurement:
    """The measurement works on real government text"""

    def test_a_grade_is_measured_for_a_real_document(self):
        response = run_simplify()

        assert response.status_code == 200
        data = response.json()
        readability = data.get("readability")

        assert readability is not None
        assert isinstance(readability["simplified"]["flesch_kincaid_grade"], (int, float))
        assert isinstance(readability["simplified"]["flesch_reading_ease"], (int, float))
        assert readability["target_grade_level"] == 5
        assert isinstance(readability["target_achieved"], bool)

    def test_the_original_text_is_measured_too(self):
        response = run_simplify()
        readability = response.json()["readability"]

        assert readability["original"]["flesch_kincaid_grade"] is not None
        assert readability["original"]["word_count"] > 0

    def test_a_word_outside_the_dictionary_does_not_break_the_measurement(self):
        """textstat raises a KeyError for an unknown word, which used to
        make the whole measurement return nothing."""
        text = "The postgraduate scholarship requires a KYC-compliant Aadhaar linked account."

        grade = readability_service.calculate_flesch_kincaid_grade(text)
        ease = readability_service.calculate_flesch_reading_ease(text)

        assert grade is not None
        assert ease is not None

    def test_a_number_in_the_text_does_not_break_the_measurement(self):
        text = "The amount of Rs. 2,50,000 is paid in two instalments of 1,25,000 each."

        assert readability_service.calculate_flesch_kincaid_grade(text) is not None

    def test_the_target_is_not_assumed_to_be_reached(self):
        """A long, technical document does not reach grade 5."""
        response = run_simplify()
        readability = response.json()["readability"]

        grade = readability["simplified"]["flesch_kincaid_grade"]
        target = readability["target_grade_level"]

        assert readability["target_achieved"] == (grade <= target)


class TestReadabilityUnavailable:
    """A measurement that cannot be made is left out, not faked"""

    def test_a_failed_measurement_does_not_fail_the_simplification(self):
        provider = FakeProvider()
        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with patch.object(llm_service, "_build_provider_chain", return_value=[provider]):
                with patch.object(
                    readability_service,
                    "compare_readability",
                    side_effect=RuntimeError("measurement failed"),
                ):
                    response = client.post(
                        "/api/documents/simplify",
                        json={"text": SOURCE, "target_grade_level": 5},
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["simplified_text"] == SIMPLIFIED
        # The measurement is simply not there.
        assert data.get("readability") is None

    def test_empty_text_has_no_measurement(self):
        metrics = readability_service.analyze_text_readability("")

        assert metrics["flesch_kincaid_grade"] is None
        assert metrics["flesch_reading_ease"] is None
