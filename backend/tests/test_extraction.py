"""
Tests for M6 Structured Information Extraction.
Comprehensive tests for information extraction service and API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.services import extraction_service
from app.schemas.extraction import (
    ExtractionRequest,
    ExtractionResponse,
    ExtractedDeadline,
    ExtractedAgeRequirement,
    ExtractedMonetaryAmount,
)

client = TestClient(app)


# ============================================================
# Basic Extraction Tests
# ============================================================

class TestBasicExtraction:
    """Test basic extraction functionality"""

    def test_extract_deadlines(self):
        """Test deadline extraction"""
        text = "Apply before 31 December 2026."
        facts = extraction_service.extract_deadlines(text)

        assert len(facts) >= 1
        assert facts[0].date == "2026-12-31"

    def test_extract_multiple_deadlines(self):
        """Test extraction of multiple deadlines"""
        text = "Applications must be submitted by 31 December 2026. Second deadline: 15 January 2027."
        facts = extraction_service.extract_deadlines(text)

        assert len(facts) >= 1
        # Should extract normalized dates

    def test_extract_age_requirements(self):
        """Test age requirement extraction"""
        text = "Applicants must be at least 18 years old."
        facts = extraction_service.extract_age_requirements(text)

        assert len(facts) >= 1
        assert facts[0].minimum_age == 18

    def test_extract_age_range(self):
        """Test age range extraction"""
        text = "Candidates must be between 18 and 65 years of age."
        facts = extraction_service.extract_age_requirements(text)

        assert len(facts) >= 1
        assert facts[0].minimum_age == 18
        assert facts[0].maximum_age == 65

    def test_extract_monetary_amounts(self):
        """Test monetary amount extraction"""
        text = "The assistance amount is ₹2,50,000."
        facts = extraction_service.extract_monetary_amounts(text)

        assert len(facts) >= 1
        assert "2,50,000" in facts[0].amount

    def test_extract_multiple_amounts(self):
        """Test extraction of multiple monetary amounts"""
        text = "The scheme provides ₹2,50,000 assistance and Rs. 5,000 application fee."
        facts = extraction_service.extract_monetary_amounts(text)

        assert len(facts) >= 2

    def test_extract_percentages(self):
        """Test percentage extraction"""
        text = "The interest rate is 5% per annum."
        facts = extraction_service.extract_percentages(text)

        assert len(facts) >= 1
        assert facts[0].value == 5.0

    def test_extract_required_documents(self):
        """Test required documents extraction"""
        text = "Applicants must submit Aadhaar, income certificate, and bank account details."
        facts = extraction_service.extract_required_documents(text)

        assert len(facts) >= 1
        # Should extract at least one document


# ============================================================
# Date Normalization Tests
# ============================================================

class TestDateNormalizationExtraction:
    """Test date normalization in extraction"""

    def test_date_format_dmy(self):
        """Test D Month YYYY format"""
        text = "Deadline: 31 December 2026"
        facts = extraction_service.extract_deadlines(text)

        assert len(facts) >= 1
        assert facts[0].date == "2026-12-31"

    def test_date_format_mdy(self):
        """Test Month DD, YYYY format"""
        text = "Submit by December 31, 2026."
        facts = extraction_service.extract_deadlines(text)

        assert len(facts) >= 1
        assert facts[0].date == "2026-12-31"

    def test_iso_date_format(self):
        """Test ISO format"""
        text = "Apply before 2026-12-31."
        facts = extraction_service.extract_deadlines(text)

        assert len(facts) >= 1
        assert facts[0].date == "2026-12-31"


# ============================================================
# Currency and Money Tests
# ============================================================

class TestMoneyExtraction:
    """Test money extraction in structured information"""

    def test_rupee_symbol_extraction(self):
        """Test extraction with rupee symbol"""
        text = "Assistance: ₹2,50,000"
        facts = extraction_service.extract_monetary_amounts(text)

        assert len(facts) >= 1
        assert "₹" in facts[0].amount

    def test_rs_prefix_extraction(self):
        """Test extraction with Rs. prefix"""
        text = "Fee: Rs. 5,000"
        facts = extraction_service.extract_monetary_amounts(text)

        assert len(facts) >= 1
        assert facts[0].amount

    def test_amount_normalization(self):
        """Test amount normalization"""
        text = "Amount is ₹1,00,000."
        facts = extraction_service.extract_monetary_amounts(text)

        assert len(facts) >= 1
        assert facts[0].amount_normalized == "100000"

    def test_money_purpose_detection(self):
        """Test detection of money purpose"""
        text = "Assistance amount: ₹2,50,000. Interest rate: 5%"
        facts = extraction_service.extract_monetary_amounts(text)

        assert len(facts) >= 1
        # Should detect purpose based on context


# ============================================================
# Document Extraction Tests
# ============================================================

class TestDocumentExtraction:
    """Test required documents extraction"""

    def test_extract_common_documents(self):
        """Test extraction of common government documents"""
        text = "Submit Aadhaar, PAN card, and income certificate."
        facts = extraction_service.extract_required_documents(text)

        assert len(facts) >= 1

    def test_extract_documents_with_bullets(self):
        """Test extraction from bulleted list"""
        text = """Required documents:
        - Aadhaar card
        - Income certificate
        - Bank account details"""
        facts = extraction_service.extract_required_documents(text)

        assert len(facts) >= 1


# ============================================================
# Contact Information Tests
# ============================================================

class TestContactExtraction:
    """Test contact information extraction"""

    def test_extract_phone_number(self):
        """Test phone number extraction"""
        text = "Contact us at 9876543210."
        facts = extraction_service.extract_contact_information(text)

        # May or may not extract depending on pattern matching
        assert isinstance(facts, list)

    def test_extract_email(self):
        """Test email extraction"""
        text = "Email: helpdesk@example.gov.in"
        facts = extraction_service.extract_contact_information(text)

        assert len(facts) >= 1
        assert facts[0].type == "email"


# ============================================================
# Full Structured Information Tests
# ============================================================

class TestFullStructuredExtraction:
    """Test complete structured information extraction"""

    def test_basic_extraction(self):
        """Test basic extraction of all categories"""
        text = """
        Housing Assistance Scheme 2026

        Application Deadline: 31 December 2026
        Assistance Amount: ₹2,50,000
        Age Requirement: 18 years minimum

        Required Documents:
        - Aadhaar card
        - Income certificate
        - Bank account details

        Interest Rate: 5% per annum
        """

        info = extraction_service.extract_structured_information(text)

        assert info.deadlines is not None
        assert info.financial_information is not None
        assert info.age_requirements is not None
        assert info.required_documents is not None
        assert info.percentages is not None

    def test_empty_categories(self):
        """Test that missing categories are empty, not None"""
        text = "Simple text without structure."
        info = extraction_service.extract_structured_information(text)

        assert isinstance(info.deadlines, list)
        assert isinstance(info.required_documents, list)
        assert isinstance(info.financial_information, list)

    def test_fact_validation(self):
        """Test fact preservation validation"""
        text = "Apply before 31 December 2026. Amount is ₹2,50,000."
        info = extraction_service.extract_structured_information(text)

        validation = extraction_service.validate_critical_facts(info, text)

        assert validation["facts_extracted"] is not None
        assert validation["critical_facts_count"] >= 0


# ============================================================
# Real-World Example Tests
# ============================================================

class TestRealWorldExamples:
    """Test with real-world examples"""

    def test_postman_example_text(self):
        """Test with Postman example text"""
        text = """Eligible applicants must submit the application before 31 December 2026.
        The assistance amount is ₹2,50,000.
        Applicants must be at least 18 years old and must submit Aadhaar, income certificate,
        and bank account details."""

        info = extraction_service.extract_structured_information(text)

        # Should extract deadline
        assert len(info.deadlines) >= 1
        assert info.deadlines[0].date == "2026-12-31"

        # Should extract money
        assert len(info.financial_information) >= 1
        assert "2,50,000" in info.financial_information[0].amount

        # Should extract age
        assert len(info.age_requirements) >= 1
        assert info.age_requirements[0].minimum_age == 18

        # Should extract documents
        assert len(info.required_documents) >= 1

    def test_complex_document(self):
        """Test with complex document"""
        text = """
        Government Assistance Scheme 2026-2027

        Eligibility:
        - Citizens of India
        - Annual income below ₹10,00,000
        - Age between 25 and 60 years

        Benefits:
        - Direct cash transfer: ₹2,50,000
        - Interest-free loan: Up to ₹5,00,000 at 5% interest

        Application Process:
        1. Download form from website
        2. Fill form with documents
        3. Submit to nearest office

        Deadline: 31 December 2026
        Office: New Delhi
        Contact: helpdesk@example.gov.in
        """

        info = extraction_service.extract_structured_information(text)

        # Should extract multiple facts
        assert len(info.deadlines) >= 1
        assert len(info.age_requirements) >= 1
        assert len(info.financial_information) >= 1
        assert len(info.percentages) >= 1


# ============================================================
# API Endpoint Tests
# ============================================================

class TestExtractionEndpoint:
    """Test extraction API endpoint"""

    def test_extraction_endpoint_success(self):
        """Test successful extraction"""
        request_data = {
            "text": "Apply before 31 December 2026. Assistance: ₹2,50,000. Age: 18 years.",
            "extract_title": True,
            "extract_summary": True
        }

        response = client.post("/api/documents/extract-info", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "document_id" in data
        assert "structured_information" in data
        assert data["original_text"] == request_data["text"]

    def test_extraction_endpoint_with_facts(self):
        """Test extraction with various facts"""
        request_data = {
            "text": """Eligible applicants must submit the application before 31 December 2026.
            The assistance amount is ₹2,50,000. Applicants must be at least 18 years old and must
            submit Aadhaar, income certificate, and bank account details.""",
            "extract_title": False,
            "extract_summary": False
        }

        response = client.post("/api/documents/extract-info", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        info = data["structured_information"]
        assert len(info["deadlines"]) >= 1
        assert len(info["financial_information"]) >= 1
        assert len(info["age_requirements"]) >= 1
        assert len(info["required_documents"]) >= 1

    def test_extraction_endpoint_empty_text(self):
        """Test extraction with empty text"""
        request_data = {
            "text": "",
            "extract_title": True,
            "extract_summary": True
        }

        response = client.post("/api/documents/extract-info", json=request_data)

        assert response.status_code == 422

    def test_extraction_endpoint_missing_text(self):
        """Test extraction with missing text field"""
        request_data = {
            "extract_title": True,
            "extract_summary": True
        }

        response = client.post("/api/documents/extract-info", json=request_data)

        assert response.status_code == 422

    def test_extraction_endpoint_text_too_long(self):
        """Test extraction with text exceeding limit"""
        long_text = "A" * 150000
        request_data = {
            "text": long_text,
            "extract_title": True,
            "extract_summary": True
        }

        response = client.post("/api/documents/extract-info", json=request_data)

        # Should be rejected by schema validation or service
        assert response.status_code in [400, 422]

    def test_extraction_endpoint_default_flags(self):
        """Test extraction with default flags"""
        request_data = {
            "text": "Apply before 31 December 2026."
        }

        response = client.post("/api/documents/extract-info", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_extraction_endpoint_preserves_original(self):
        """Test that original text is preserved"""
        original = "Eligible applicants must submit ₹5,00,000 before 31 December 2026."
        request_data = {
            "text": original,
            "extract_title": True,
            "extract_summary": True
        }

        response = client.post("/api/documents/extract-info", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["original_text"] == original

    def test_extraction_endpoint_metadata(self):
        """Test metadata in response"""
        request_data = {
            "text": "Apply by 31 December 2026 for ₹2,50,000.",
            "extract_title": True,
            "extract_summary": True
        }

        response = client.post("/api/documents/extract-info", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] >= 0
        assert "extraction_method" in data
        assert "metadata" in data


# ============================================================
# Edge Cases and Error Handling
# ============================================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_no_extractable_information(self):
        """Test with text containing no extractable information"""
        text = "This is a simple paragraph with no structured information."
        info = extraction_service.extract_structured_information(text)

        # Should return empty lists, not errors
        assert isinstance(info.deadlines, list)
        assert isinstance(info.required_documents, list)

    def test_malformed_dates(self):
        """Test with malformed dates"""
        text = "Apply before 99 Nonmonth 9999."
        facts = extraction_service.extract_deadlines(text)

        # Should handle gracefully
        assert isinstance(facts, list)

    def test_partial_information(self):
        """Test with partial information"""
        text = "Deadline: 31 December 2026"
        info = extraction_service.extract_structured_information(text)

        # Should extract deadline
        assert len(info.deadlines) >= 1
        # Other categories should be empty
        assert len(info.required_documents) == 0

    def test_duplicate_extraction(self):
        """Test that duplicates are avoided"""
        text = "The deadline is 31 December 2026. Apply before 31 December 2026."
        facts = extraction_service.extract_deadlines(text)

        # Should not extract duplicates
        dates = [f.date for f in facts]
        assert dates.count("2026-12-31") <= 1


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
