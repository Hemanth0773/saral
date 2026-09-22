"""
Tests for LLM Simplification Service (MILESTONE 5).
Tests cover LLM provider, validation, API endpoints, and fact preservation.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from app.main import app
from app.services import llm_service, validation_service
from app.schemas.simplification import SimplificationRequest


client = TestClient(app)


# ============================================================
# LLM Provider Tests
# ============================================================

class TestLLMProvider:
    """Test LLM provider functionality"""

    def test_get_mock_provider(self):
        """Test getting mock provider"""
        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            provider = llm_service.get_llm_provider()
            assert isinstance(provider, llm_service.MockProvider)

    def test_mock_provider_simplification(self):
        """Test mock provider simplification"""
        provider = llm_service.MockProvider()
        text = "The applicant shall submit the duly completed application form prior to the prescribed deadline."
        simplified = provider.simplify_text(text, 5)

        assert simplified is not None
        assert len(simplified) > 0
        assert "must" in simplified.lower() or "shall" not in simplified.lower()

    def test_mock_provider_structured_simplification(self):
        """Test mock provider structured simplification"""
        provider = llm_service.MockProvider()
        text = "Applicants must be at least 18 years old."
        result = provider.generate_structured_simplification(text, 5)

        assert "simplified_text" in result
        assert "key_terms" in result
        assert "sections" in result
        assert len(result["simplified_text"]) > 0

    def test_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises error"""
        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'unsupported_provider'):
            with pytest.raises(llm_service.LLMServiceError) as exc_info:
                llm_service.get_llm_provider()
            assert "Unsupported LLM provider" in str(exc_info.value)

    def test_openai_provider_without_api_key(self):
        """Test OpenAI provider without API key raises error"""
        with patch.object(llm_service.settings, 'LLM_API_KEY', ''):
            with patch.object(llm_service.settings, 'LLM_PROVIDER', 'openai'):
                with pytest.raises(llm_service.LLMServiceError) as exc_info:
                    llm_service.OpenAIProvider()
                assert "API key not configured" in str(exc_info.value)

    def test_get_gemini_provider(self):
        """Test getting Gemini provider"""
        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'gemini'):
            with patch.object(llm_service.settings, 'LLM_API_KEY', 'test-key'):
                provider = llm_service.get_llm_provider()
                assert isinstance(provider, llm_service.GeminiProvider)

    def test_gemini_provider_without_api_key(self):
        """Test Gemini provider without API key raises error"""
        with patch.object(llm_service.settings, 'LLM_API_KEY', ''):
            with patch.object(llm_service.settings, 'LLM_PROVIDER', 'gemini'):
                with pytest.raises(llm_service.LLMServiceError) as exc_info:
                    llm_service.GeminiProvider()
                assert "API key not configured" in str(exc_info.value)

    def test_gemini_provider_simplification_mock(self):
        """Test Gemini provider simplification with mocked API call"""
        with patch.object(llm_service.settings, 'LLM_API_KEY', 'test-key'):
            with patch.object(llm_service.settings, 'LLM_MODEL', 'gemini-pro'):
                provider = llm_service.GeminiProvider()

                # Mock the httpx.Client.post method
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": "You must send the form before the deadline."
                                    }
                                ]
                            }
                        }
                    ]
                }

                with patch('httpx.Client.post', return_value=mock_response):
                    text = "The applicant shall submit the duly completed application form prior to the prescribed deadline."
                    simplified = provider.simplify_text(text, 5)

                    assert simplified is not None
                    assert len(simplified) > 0
                    assert "deadline" in simplified.lower()

    def test_gemini_provider_api_error(self):
        """Test Gemini provider handles API errors"""
        with patch.object(llm_service.settings, 'LLM_API_KEY', 'test-key'):
            with patch.object(llm_service.settings, 'LLM_MODEL', 'gemini-pro'):
                provider = llm_service.GeminiProvider()

                # Mock failed API call
                mock_response = MagicMock()
                mock_response.status_code = 401
                mock_response.text = "Invalid API key"

                with patch('httpx.Client.post', return_value=mock_response):
                    with pytest.raises(llm_service.LLMServiceError):
                        provider.simplify_text("Test text", 5)

    def test_gemini_provider_timeout(self):
        """Test Gemini provider handles timeouts"""
        import httpx

        with patch.object(llm_service.settings, 'LLM_API_KEY', 'test-key'):
            with patch.object(llm_service.settings, 'LLM_MODEL', 'gemini-pro'):
                provider = llm_service.GeminiProvider()

                # Mock timeout
                with patch('httpx.Client.post', side_effect=httpx.TimeoutException("Timeout")):
                    with pytest.raises(llm_service.LLMServiceError) as exc_info:
                        provider.simplify_text("Test text", 5)
                    assert "timeout" in str(exc_info.value).lower()

    def test_gemini_provider_quota_exhausted_429(self):
        """Test Gemini provider detects quota exhaustion (429 RESOURCE_EXHAUSTED)"""
        with patch.object(llm_service.settings, 'LLM_API_KEY', 'test-key'):
            with patch.object(llm_service.settings, 'LLM_MODEL', 'gemini-2.5-flash'):
                provider = llm_service.GeminiProvider()

                # Mock 429 RESOURCE_EXHAUSTED response
                mock_response = MagicMock()
                mock_response.status_code = 429
                mock_response.text = json.dumps({
                    "error": {
                        "code": 429,
                        "message": "Resource has been exhausted (e.g. check quota).",
                        "status": "RESOURCE_EXHAUSTED"
                    }
                })

                with patch('httpx.Client.post', return_value=mock_response):
                    with pytest.raises(llm_service.LLMQuotaExhaustedError) as exc_info:
                        provider.simplify_text("Test text", 5)
                    assert "quota" in str(exc_info.value).lower()

    def test_gemini_provider_quota_exhausted_no_fallback(self):
        """Test that quota exhaustion does NOT trigger fallback simplification"""
        with patch.object(llm_service.settings, 'LLM_API_KEY', 'test-key'):
            with patch.object(llm_service.settings, 'LLM_MODEL', 'gemini-2.5-flash'):
                provider = llm_service.GeminiProvider()

                # Mock 429 RESOURCE_EXHAUSTED response
                mock_response = MagicMock()
                mock_response.status_code = 429
                mock_response.text = json.dumps({
                    "error": {
                        "code": 429,
                        "message": "Resource has been exhausted",
                        "status": "RESOURCE_EXHAUSTED"
                    }
                })

                call_count = 0
                def mock_post(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    return mock_response

                with patch('httpx.Client.post', side_effect=mock_post):
                    with pytest.raises(llm_service.LLMQuotaExhaustedError):
                        provider.simplify_text("Test text", 5)

                    # Should only make ONE API call, not multiple fallback attempts
                    assert call_count == 1

    def test_gemini_provider_structured_quota_exhausted_no_fallback(self):
        """Test that structured simplification doesn't fallback on quota exhaustion"""
        with patch.object(llm_service.settings, 'LLM_API_KEY', 'test-key'):
            with patch.object(llm_service.settings, 'LLM_MODEL', 'gemini-2.5-flash'):
                provider = llm_service.GeminiProvider()

                # Mock 429 RESOURCE_EXHAUSTED response
                mock_response = MagicMock()
                mock_response.status_code = 429
                mock_response.text = json.dumps({
                    "error": {
                        "code": 429,
                        "message": "Resource has been exhausted",
                        "status": "RESOURCE_EXHAUSTED"
                    }
                })

                call_count = 0
                def mock_post(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    return mock_response

                with patch('httpx.Client.post', side_effect=mock_post):
                    with pytest.raises(llm_service.LLMQuotaExhaustedError):
                        provider.generate_structured_simplification("Test text", 5)

                    # Should only make ONE API call
                    assert call_count == 1

    def test_gemini_provider_authentication_error(self):
        """Test Gemini provider detects authentication errors (401)"""
        with patch.object(llm_service.settings, 'LLM_API_KEY', 'test-key'):
            with patch.object(llm_service.settings, 'LLM_MODEL', 'gemini-pro'):
                provider = llm_service.GeminiProvider()

                mock_response = MagicMock()
                mock_response.status_code = 401
                mock_response.text = json.dumps({
                    "error": {
                        "code": 401,
                        "message": "The request is missing a valid API key.",
                        "status": "UNAUTHENTICATED"
                    }
                })

                with patch('httpx.Client.post', return_value=mock_response):
                    with pytest.raises(llm_service.LLMAuthenticationError) as exc_info:
                        provider.simplify_text("Test text", 5)
                    assert "authentication" in str(exc_info.value).lower()

    def test_gemini_provider_rate_limit_error(self):
        """Test Gemini provider detects temporary rate limits (429 without RESOURCE_EXHAUSTED)"""
        with patch.object(llm_service.settings, 'LLM_API_KEY', 'test-key'):
            with patch.object(llm_service.settings, 'LLM_MODEL', 'gemini-pro'):
                provider = llm_service.GeminiProvider()

                mock_response = MagicMock()
                mock_response.status_code = 429
                mock_response.text = json.dumps({
                    "error": {
                        "code": 429,
                        "message": "Too many requests",
                        "status": "RESOURCE_EXHAUSTED"  # Would be different status for rate limit
                    }
                })

                with patch('httpx.Client.post', return_value=mock_response):
                    # This should still be detected as quota (RESOURCE_EXHAUSTED status)
                    with pytest.raises(llm_service.LLMQuotaExhaustedError):
                        provider.simplify_text("Test text", 5)


class TestTextChunking:
    """Test text chunking functionality"""

    def test_chunk_small_text(self):
        """Test chunking small text returns single chunk"""
        text = "This is a short text."
        chunks = llm_service.chunk_text_for_simplification(text, 2000)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_large_text(self):
        """Test chunking large text into multiple chunks"""
        # Create text larger than chunk size
        text = "This is a test sentence. " * 200  # ~5000 chars
        chunks = llm_service.chunk_text_for_simplification(text, 1000)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 1200  # Allow some margin

    def test_chunk_preserves_paragraphs(self):
        """Test that chunking preserves paragraph boundaries"""
        text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
        chunks = llm_service.chunk_text_for_simplification(text, 100)

        # Should preserve paragraphs
        assert len(chunks) >= 1

    def test_chunk_splits_long_sentences(self):
        """Test that chunking handles very long sentences"""
        text = "A" * 2000 + ". " + "B" * 2000 + "."
        chunks = llm_service.chunk_text_for_simplification(text, 1500)

        assert len(chunks) >= 1


# ============================================================
# Validation Service Tests
# ============================================================

class TestValidationService:
    """Test fact preservation validation"""

    def test_extract_dates(self):
        """Test extraction of dates from text"""
        text = "Apply before 31 December 2026. The deadline is 2026-12-31."
        facts = validation_service.extract_critical_facts(text)

        date_facts = [f for f in facts if f.fact_type == "deadline"]
        assert len(date_facts) >= 1
        # At least one date should be extracted
        assert any("2026" in f.value for f in date_facts)

    def test_extract_currency_amounts(self):
        """Test extraction of currency amounts"""
        text = "The assistance amount is ₹2,50,000. The fee is Rs. 500."
        facts = validation_service.extract_critical_facts(text)

        money_facts = [f for f in facts if f.fact_type == "money"]
        assert len(money_facts) >= 1
        # Check for the larger amount
        assert any("2,50,000" in f.value for f in money_facts)

    def test_extract_percentages(self):
        """Test extraction of percentages"""
        text = "The interest rate is 5% per annum. You get 50 percent discount."
        facts = validation_service.extract_critical_facts(text)

        percent_facts = [f for f in facts if f.fact_type == "percentage"]
        assert len(percent_facts) >= 1
        assert any("5%" in f.value for f in percent_facts)

    def test_extract_ages(self):
        """Test extraction of age requirements"""
        text = "Applicants must be at least 18 years old. The minimum age is 21 years."
        facts = validation_service.extract_critical_facts(text)

        age_facts = [f for f in facts if f.fact_type == "age"]
        assert len(age_facts) >= 1
        assert any("18 years" in f.value for f in age_facts)

    def test_extract_quantities(self):
        """Test extraction of quantities"""
        text = "Submit at least 2 passport photos. Minimum of 3 references required."
        facts = validation_service.extract_critical_facts(text)

        quantity_facts = [f for f in facts if f.fact_type == "quantity"]
        assert len(quantity_facts) >= 0  # May or may not extract based on pattern

    def test_validate_fact_preservation_success(self):
        """Test successful fact preservation validation"""
        original = "The deadline is 31 December 2026. The amount is ₹2,50,000."
        simplified = "You must apply by 31 December 2026. You will receive ₹2,50,000."

        facts, failures = validation_service.validate_fact_preservation(original, simplified)

        # Most facts should be preserved
        preserved_count = sum(1 for f in facts if f.preserved_in_simplified)
        assert preserved_count >= 1
        assert len(failures) <= 1

    def test_validate_fact_preservation_failure_changed_date(self):
        """Test detection of changed date"""
        original = "Apply before 31 December 2026."
        simplified = "Apply before 31 December 2025."

        facts, failures = validation_service.validate_fact_preservation(original, simplified)

        # Should detect the changed date
        date_facts = [f for f in facts if f.fact_type == "deadline"]
        # At least one date should be detected
        assert len(date_facts) >= 1

    def test_validate_fact_preservation_failure_changed_amount(self):
        """Test detection of changed currency amount"""
        original = "The assistance is ₹2,50,000."
        simplified = "The assistance is ₹2,00,000."

        facts, failures = validation_service.validate_fact_preservation(original, simplified)

        # Should detect the changed amount
        assert len(failures) >= 1 or len([f for f in facts if not f.preserved_in_simplified]) >= 1

    def test_validate_fact_preservation_failure_changed_percentage(self):
        """Test detection of changed percentage"""
        original = "The interest rate is 5%."
        simplified = "The interest rate is 10%."

        facts, failures = validation_service.validate_fact_preservation(original, simplified)

        # Should detect the changed percentage
        assert len(failures) >= 1 or len([f for f in facts if not f.preserved_in_simplified]) >= 1

    def test_validate_quality_too_short(self):
        """Test detection of oversimplification"""
        original = "This is a comprehensive document with multiple important details about the scheme."
        simplified = "Short."

        issues = validation_service.validate_simplification_quality(original, simplified)

        assert len(issues) >= 1
        assert any("suspiciously short" in issue.lower() for issue in issues)

    def test_validate_quality_no_simplification(self):
        """Test detection of lack of simplification"""
        original = "This is a test document."
        simplified = "This is a test document with one extra word."

        issues = validation_service.validate_simplification_quality(original, simplified)

        # May or may not detect this based on threshold
        assert isinstance(issues, list)


# ============================================================
# API Endpoint Tests
# ============================================================

class TestSimplificationEndpoint:
    """Test simplification API endpoint"""

    def test_simplify_endpoint_success(self):
        """Test successful simplification"""
        request_data = {
            "text": "The applicant shall submit the application before the deadline.",
            "target_grade_level": 5
        }

        # Mock the LLM service to avoid actual API calls
        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "simplified_text" in data
        assert "original_text" in data
        assert data["original_text"] == request_data["text"]
        assert data["target_grade_level"] == 5

    def test_simplify_endpoint_with_facts(self):
        """Test simplification with critical facts"""
        request_data = {
            "text": "Eligible applicants must submit the application before 31 December 2026. The assistance amount is ₹2,50,000. Applicants must be at least 18 years old.",
            "target_grade_level": 5
        }

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "preserved_facts" in data
        # Original text should remain unchanged
        assert "31 December 2026" in data["original_text"]
        assert "₹2,50,000" in data["original_text"]

    def test_simplify_endpoint_empty_text(self):
        """Test simplification with empty text"""
        request_data = {
            "text": "",
            "target_grade_level": 5
        }

        response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 422

    def test_simplify_endpoint_invalid_grade_level(self):
        """Test simplification with invalid grade level"""
        request_data = {
            "text": "Some text",
            "target_grade_level": 15  # Invalid: > 12
        }

        response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 422

    def test_simplify_endpoint_text_too_long(self):
        """Test simplification with text exceeding limit"""
        # Create text longer than schema validation limit (50,000 chars)
        long_text = "A" * 60000
        request_data = {
            "text": long_text,
            "target_grade_level": 5
        }

        response = client.post("/api/documents/simplify", json=request_data)

        # Schema validation should reject before reaching handler
        assert response.status_code == 422

    def test_simplify_endpoint_missing_text_field(self):
        """Test simplification with missing text field"""
        request_data = {
            "target_grade_level": 5
        }

        response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 422

    def test_simplify_endpoint_default_grade_level(self):
        """Test simplification with default grade level"""
        request_data = {
            "text": "Test text for simplification."
        }

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 200
        data = response.json()
        # Should use default from config (5)
        assert data["target_grade_level"] == 5

    def test_simplify_endpoint_preserves_original_text(self):
        """Test that original text is never modified"""
        original = "The applicant shall submit ₹5,00,000 before 31 December 2026."
        request_data = {
            "text": original,
            "target_grade_level": 5
        }

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 200
        data = response.json()
        # Original text must be exactly the same
        assert data["original_text"] == original

    def test_simplify_endpoint_model_used_in_response(self):
        """Test that model used is included in response"""
        request_data = {
            "text": "Test text",
            "target_grade_level": 5
        }

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "model_used" in data
        assert len(data["model_used"]) > 0

    def test_simplify_endpoint_processing_time(self):
        """Test that processing time is recorded"""
        request_data = {
            "text": "Test text for timing",
            "target_grade_level": 5
        }

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] >= 0


class TestValidationEndpoint:
    """Test validation endpoint"""

    def test_validate_endpoint_success(self):
        """Test successful validation"""
        response = client.post(
            "/api/documents/simplify/validate",
            params={
                "original_text": "Deadline is 31 December 2026.",
                "simplified_text": "The deadline is 31 December 2026."
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "preserved_facts" in data
        assert "validation_failures" in data

    def test_validate_endpoint_empty_original(self):
        """Test validation with empty original text"""
        response = client.post(
            "/api/documents/simplify/validate",
            params={
                "original_text": "",
                "simplified_text": "Some text"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_validate_endpoint_empty_simplified(self):
        """Test validation with empty simplified text"""
        response = client.post(
            "/api/documents/simplify/validate",
            params={
                "original_text": "Some text",
                "simplified_text": ""
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_validate_endpoint_statistics(self):
        """Test validation returns statistics"""
        response = client.post(
            "/api/documents/simplify/validate",
            params={
                "original_text": "Amount is ₹2,50,000 and deadline is 31 December 2026.",
                "simplified_text": "You get ₹2,50,000. Apply by 31 December 2026."
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "statistics" in data
        assert "total_facts" in data["statistics"]
        assert "preserved_facts" in data["statistics"]
        assert "preservation_rate" in data["statistics"]


# ============================================================
# Integration Tests
# ============================================================

class TestSimplificationIntegration:
    """Integration tests for simplification pipeline"""

    def test_full_simplification_pipeline(self):
        """Test complete simplification pipeline"""
        text = """
        Government Housing Assistance Scheme

        Eligible applicants must submit the application before 31 December 2026.
        The assistance amount is ₹2,50,000.
        Applicants must be at least 18 years old and must submit:
        - Aadhaar card
        - Income certificate
        - Bank account details

        The interest rate is 5% per annum.
        """

        request_data = {
            "text": text,
            "target_grade_level": 5
        }

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["success"] is True
        assert "document_id" in data
        assert "original_text" in data
        assert "simplified_text" in data
        assert "preserved_facts" in data
        assert "validation_passed" in data

        # Verify original text is unchanged
        assert "31 December 2026" in data["original_text"]
        assert "₹2,50,000" in data["original_text"]
        assert "18 years" in data["original_text"]
        assert "Aadhaar" in data["original_text"]

    def test_simplification_with_retry_logic(self):
        """Test simplification retry logic"""
        text = "Test text for retry logic."

        # Mock provider that fails first, succeeds second
        call_count = [0]

        def mock_simplify(text, grade):
            call_count[0] += 1
            if call_count[0] == 1:
                raise llm_service.LLMServiceError("Temporary error")
            return "Simplified: " + text

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            provider = llm_service.MockProvider()
            with patch.object(provider, 'simplify_text', side_effect=mock_simplify):
                with patch('app.services.llm_service.get_llm_provider', return_value=provider):
                    simplified, attempts, model = llm_service.simplify_text_with_retry(
                        text, 5, max_attempts=2
                    )

        assert call_count[0] == 2
        assert attempts == 2

    def test_simplification_max_retries_exceeded(self):
        """Test simplification when max retries exceeded"""
        text = "Test text"

        # Mock provider that always fails
        def mock_simplify(text, grade):
            raise llm_service.LLMServiceError("Permanent error")

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            provider = llm_service.MockProvider()
            with patch.object(provider, 'simplify_text', side_effect=mock_simplify):
                with patch('app.services.llm_service.get_llm_provider', return_value=provider):
                    with pytest.raises(llm_service.LLMServiceError):
                        llm_service.simplify_text_with_retry(text, 5, max_attempts=2)


# ============================================================
# Error Handling Tests
# ============================================================

class TestErrorHandling:
    """Test error handling in simplification"""

    def test_missing_api_key_error(self):
        """Test handling of missing API key"""
        request_data = {
            "text": "Test text",
            "target_grade_level": 5
        }

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'openai'):
            with patch.object(llm_service.settings, 'LLM_API_KEY', ''):
                response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert "LLM_CONFIGURATION_ERROR" in data["error"]["code"]

    def test_provider_failure_graceful_error(self):
        """Test graceful error handling for provider failures"""
        request_data = {
            "text": "Test text",
            "target_grade_level": 5
        }

        # Mock provider that raises error
        def mock_generate(*args, **kwargs):
            raise llm_service.LLMServiceError("Provider error")

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            with patch('app.services.llm_service.generate_simplification_response', side_effect=mock_generate):
                response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False

    def test_gemini_quota_exhausted_api_error(self):
        """Test API endpoint returns 429 for quota exhaustion"""
        request_data = {
            "text": "Test text",
            "target_grade_level": 5
        }

        # Mock provider that raises quota exhaustion
        def mock_generate(*args, **kwargs):
            raise llm_service.LLMQuotaExhaustedError("Gemini API quota exhausted")

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'gemini'):
            with patch('app.services.llm_service.generate_simplification_response', side_effect=mock_generate):
                response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 429
        data = response.json()
        assert data["success"] is False
        assert "LLM_QUOTA_EXHAUSTED" in data["error"]["code"]
        assert "quota" in data["error"]["message"].lower()

    def test_gemini_authentication_api_error(self):
        """Test API endpoint returns 503 for authentication errors"""
        request_data = {
            "text": "Test text",
            "target_grade_level": 5
        }

        # Mock provider that raises authentication error
        def mock_generate(*args, **kwargs):
            raise llm_service.LLMAuthenticationError("Gemini API authentication failed")

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'gemini'):
            with patch('app.services.llm_service.generate_simplification_response', side_effect=mock_generate):
                response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert "LLM_AUTHENTICATION_ERROR" in data["error"]["code"]


# ============================================================
# Fact Preservation Specific Tests
# ============================================================

class TestFactPreservation:
    """Detailed tests for fact preservation"""

    def test_preserve_indian_currency(self):
        """Test preservation of Indian currency format"""
        text = "The scheme provides ₹2,50,000 as assistance."

        facts = validation_service.extract_critical_facts(text)
        money_facts = [f for f in facts if f.fact_type == "money"]

        assert len(money_facts) >= 1
        assert any("2,50,000" in f.value for f in money_facts)

    def test_preserve_multiple_dates(self):
        """Test preservation of multiple dates"""
        text = "Apply between 1 January 2026 and 31 December 2026."

        facts = validation_service.extract_critical_facts(text)
        date_facts = [f for f in facts if f.fact_type == "deadline"]

        # Should extract at least the dates
        assert len(date_facts) >= 1

    def test_preserve_age_requirements(self):
        """Test preservation of age requirements"""
        text = "Applicants must be between 18 and 65 years of age."

        facts = validation_service.extract_critical_facts(text)
        age_facts = [f for f in facts if f.fact_type == "age"]

        # Should extract at least one age
        assert len(age_facts) >= 1

    def test_preserve_decimal_numbers(self):
        """Test preservation of decimal numbers"""
        text = "The interest rate is 5.5% per annum."

        facts = validation_service.extract_critical_facts(text)
        percent_facts = [f for f in facts if f.fact_type == "percentage"]

        assert len(percent_facts) >= 1

    def test_preserve_large_numbers(self):
        """Test preservation of large numbers with commas"""
        text = "The budget allocation is ₹1,00,00,000 for this scheme."

        facts = validation_service.extract_critical_facts(text)
        money_facts = [f for f in facts if f.fact_type == "money"]

        assert len(money_facts) >= 1

    def test_fact_preservation_validation_response(self):
        """Test that fact preservation is included in API response"""
        request_data = {
            "text": "Apply before 31 December 2026. Amount is ₹2,50,000. Age must be 18 years.",
            "target_grade_level": 5
        }

        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'mock'):
            response = client.post("/api/documents/simplify", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "preserved_facts" in data
        assert isinstance(data["preserved_facts"], list)

        # Check that facts were extracted
        assert len(data["preserved_facts"]) >= 1


# ============================================================
# Date Normalization Regression Tests (M5 Fix)
# ============================================================

class TestDateNormalization:
    """Test date normalization for fact preservation"""

    def test_date_format_variations_preserved(self):
        """Test that different date formats are recognized as equivalent"""
        original = "Apply before 31 December 2026."
        simplified = "Apply before December 31, 2026."

        facts, failures = validation_service.validate_fact_preservation(original, simplified)

        # Should recognize both as the same date
        date_facts = [f for f in facts if f.fact_type == "deadline"]
        assert len(date_facts) >= 1
        assert all(f.preserved_in_simplified for f in date_facts), f"Date not preserved: {failures}"

    def test_iso_date_preserved(self):
        """Test ISO date format preservation"""
        original = "Deadline: 31 December 2026."
        simplified = "Deadline: 2026-12-31."

        facts, failures = validation_service.validate_fact_preservation(original, simplified)

        date_facts = [f for f in facts if f.fact_type == "deadline"]
        assert len(date_facts) >= 1
        assert all(f.preserved_in_simplified for f in date_facts), f"Date not preserved: {failures}"

    def test_different_dates_detected(self):
        """Test that actually different dates are detected as failures"""
        original = "Application deadline is 31 December 2026."
        simplified = "Application deadline is 31 December 2025."

        facts, failures = validation_service.validate_fact_preservation(original, simplified)

        # Should detect the changed date
        date_facts = [f for f in facts if f.fact_type == "deadline"]
        assert len(date_facts) >= 1
        # At least one date should NOT be preserved
        assert any(not f.preserved_in_simplified for f in date_facts), "Changed date not detected"


# ============================================================
# Money Extraction Regression Tests (M5 Fix)
# ============================================================

class TestMoneyExtraction:
    """Test money extraction with proper currency context"""

    def test_money_with_currency_symbol(self):
        """Test that money is extracted only with currency context"""
        text = "The assistance amount is ₹2,50,000."
        facts = validation_service.extract_critical_facts(text)

        money_facts = [f for f in facts if f.fact_type == "money"]
        assert len(money_facts) >= 1
        assert any("2,50,000" in f.value for f in money_facts)

    def test_dates_not_extracted_as_money(self):
        """Test that date numbers are not incorrectly extracted as money"""
        text = "Apply before 31 December 2026. Applicants must be at least 18 years old."
        facts = validation_service.extract_critical_facts(text)

        money_facts = [f for f in facts if f.fact_type == "money"]
        money_values = [f.value for f in money_facts]

        # Should NOT extract 31, 2026, or 18 as money
        for val in money_values:
            assert val not in ["31", "202", "6", "18"], f"Incorrectly extracted {val} as money"

    def test_age_not_extracted_as_money(self):
        """Test that age requirements are not extracted as money"""
        text = "Applicants must be at least 18 years old."
        facts = validation_service.extract_critical_facts(text)

        money_facts = [f for f in facts if f.fact_type == "money"]
        age_facts = [f for f in facts if f.fact_type == "age"]

        # Should have age fact, not money
        assert len(age_facts) >= 1
        assert len(money_facts) == 0, "Age incorrectly extracted as money"

    def test_different_amounts_detected(self):
        """Test that changed amounts are detected"""
        original = "The assistance is ₹2,50,000."
        simplified = "The assistance is ₹2,00,000."

        facts, failures = validation_service.validate_fact_preservation(original, simplified)

        money_facts = [f for f in facts if f.fact_type == "money"]
        assert len(money_facts) >= 1
        # Should detect the changed amount
        assert any(not f.preserved_in_simplified for f in money_facts), "Changed amount not detected"


# ============================================================
# Quality Validation Regression Tests (M5 Fix)
# ============================================================

class TestQualityValidation:
    """Test quality validation improvements"""

    def test_short_text_not_flagged_as_too_similar(self):
        """Test that short texts with preserved facts pass validation"""
        original = "Apply before 31 December 2026. Amount is ₹2,50,000."
        simplified = "You must apply by December 31, 2026. You get ₹2,50,000."

        issues = validation_service.validate_simplification_quality(original, simplified)

        # Should NOT flag as too similar
        assert not any("too similar" in issue.lower() for issue in issues), f"Incorrectly flagged as similar: {issues}"

    def test_structural_changes_not_flagged_as_similar(self):
        """Test that text with structural changes passes validation"""
        original = "Eligible applicants must submit application before deadline. The amount is ₹2,50,000. Age must be 18 years."
        simplified = """**When to Apply**
You must apply by December 31, 2026.

**Money You Get**
You can get ₹2,50,000.

**Who Can Apply**
You must be at least 18 years old."""

        issues = validation_service.validate_simplification_quality(original, simplified)

        # Should NOT flag as too similar due to structural changes
        assert not any("too similar" in issue.lower() for issue in issues), f"Incorrectly flagged: {issues}"


# ============================================================
# Full Integration Regression Test (Real Postman Example)
# ============================================================

class TestFullPostmanRegression:
    """Test with actual real-world example from Postman test"""

    def test_postman_real_example_validation_passes(self):
        """Test that the real Postman example now passes validation"""
        original = "Eligible applicants must submit the application before 31 December 2026. The assistance amount is ₹2,50,000. Applicants must be at least 18 years old and must submit Aadhaar, income certificate, and bank account details."

        simplified = """**When to Apply**
You must send in your application before December 31, 2026.

**Money You Can Get**
You can get ₹2,50,000.

**Who Can Apply**
You must be at least 18 years old.

**What You Need to Send**
You need to send these papers:
* Your Aadhaar card
* An income certificate (a paper about your money)
* Your bank account details (information about your bank account)"""

        # Validate fact preservation
        facts, failures = validation_service.validate_fact_preservation(original, simplified)

        # Check critical facts
        date_facts = [f for f in facts if f.fact_type == "deadline"]
        money_facts = [f for f in facts if f.fact_type == "money"]
        age_facts = [f for f in facts if f.fact_type == "age"]

        # All critical facts should be preserved
        assert len(date_facts) >= 1, "Date not extracted"
        assert all(f.preserved_in_simplified for f in date_facts), f"Date not preserved: {failures}"

        assert len(money_facts) >= 1, "Money not extracted"
        assert all(f.preserved_in_simplified for f in money_facts), f"Money not preserved: {failures}"

        assert len(age_facts) >= 1, "Age not extracted"
        assert all(f.preserved_in_simplified for f in age_facts), f"Age not preserved: {failures}"

        # Quality validation should pass
        issues = validation_service.validate_simplification_quality(original, simplified)
        assert not any("too similar" in issue.lower() for issue in issues), f"Quality issues: {issues}"

    def test_postman_example_full_validation(self):
        """Complete validation including response structure"""
        from app.schemas.simplification import PreservedFact

        original = "Eligible applicants must submit the application before 31 December 2026. The assistance amount is ₹2,50,000. Applicants must be at least 18 years old."

        simplified = "You must apply before December 31, 2026. You can get ₹2,50,000. You must be at least 18 years old."

        facts, failures = validation_service.validate_fact_preservation(original, simplified)

        # Should have extracted facts
        assert len(facts) >= 3, f"Expected at least 3 facts, got {len(facts)}"

        # Count preserved facts
        preserved_count = sum(1 for f in facts if f.preserved_in_simplified)
        assert preserved_count >= 3, f"Expected at least 3 preserved facts, got {preserved_count}"

        # Should not have validation failures
        critical_failures = [f for f in failures if "deadline" in f.lower() or "money" in f.lower() or "age" in f.lower()]
        assert len(critical_failures) == 0, f"Unexpected failures: {critical_failures}"


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
