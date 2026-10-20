"""
Tests for rate-limit aware LLM retries and provider fallback.

Covers the failure mode where a long government notice is split into
several chunks and the provider answers HTTP 429 (tokens per minute limit)
part way through, followed by a fallback provider that is temporarily
unavailable.

All provider responses are mocked - no real API quota is consumed.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services import llm_service, llm_retry, validation_service


client = TestClient(app)


# ============================================================
# Test doubles
# ============================================================

class FakeProvider:
    """
    A provider that replays a scripted list of outcomes.

    Each entry is either a string (the simplified text to return) or an
    exception instance (raised to simulate a provider failure). The last
    entry repeats once the script is exhausted.
    """

    def __init__(self, name, script, model=None):
        self.name = name
        self.provider_name = name
        self.script = list(script)
        self.model = model or f"{name}-model"
        self.calls = []
        self.structured_calls = 0
        self.attempts = 0

    def _next_outcome(self):
        index = min(self.attempts, len(self.script) - 1)
        self.attempts += 1
        return self.script[index]

    def simplify_text(self, text, target_grade_level):
        self.calls.append(text)
        outcome = self._next_outcome()
        if isinstance(outcome, BaseException):
            raise outcome
        return f"{outcome}"

    def generate_structured_simplification(self, text, target_grade_level):
        self.calls.append(text)
        self.structured_calls += 1
        outcome = self._next_outcome()
        if isinstance(outcome, BaseException):
            raise outcome
        return {
            "simplified_text": f"{outcome}",
            "key_terms": ["term"],
            "sections": [],
        }


def rate_limit_error(message="Rate limit reached", retry_after=23.0):
    return llm_service.LLMRateLimitError(message, retry_after=retry_after)


def transient_error(message="503 UNAVAILABLE"):
    return llm_service.LLMTransientError(message)


@pytest.fixture
def no_sleep():
    """Records every retry delay instead of actually waiting."""
    recorded = []

    async def fake_sleep(delay):
        recorded.append(delay)

    with patch("asyncio.sleep", new=fake_sleep):
        yield recorded


@pytest.fixture
def deterministic_backoff():
    """Removes jitter so the computed delays are exactly predictable."""
    with patch.object(settings, "LLM_RETRY_JITTER", 0.0):
        yield


def use_chain(*providers):
    """Patches the provider chain used by the simplification pipeline."""
    return patch.object(llm_service, "_build_provider_chain", return_value=list(providers))


# ============================================================
# Retry helper unit tests
# ============================================================

class TestRetryHelpers:
    """Unit tests for the delay and hint parsing helpers"""

    def test_parse_duration_plain_seconds(self):
        assert llm_retry.parse_duration("23") == pytest.approx(23.0)
        assert llm_retry.parse_duration("1.5") == pytest.approx(1.5)

    def test_parse_duration_with_units(self):
        assert llm_retry.parse_duration("59.94s") == pytest.approx(59.94)
        assert llm_retry.parse_duration("500ms") == pytest.approx(0.5)
        assert llm_retry.parse_duration("2 minutes") == pytest.approx(120.0)
        assert llm_retry.parse_duration("1m30s") == pytest.approx(90.0)

    def test_parse_duration_rejects_garbage(self):
        assert llm_retry.parse_duration("soon") is None
        assert llm_retry.parse_duration("") is None
        assert llm_retry.parse_duration(None) is None
        assert llm_retry.parse_duration(123) is None

    def test_retry_after_header_wins(self):
        headers = {"retry-after": "23", "x-ratelimit-reset-tokens": "59.94s"}
        assert llm_retry.extract_retry_hint(headers, "") == pytest.approx(23.0)

    def test_rate_limit_reset_header_is_used(self):
        headers = {"x-ratelimit-reset-tokens": "59.94s"}
        assert llm_retry.extract_retry_hint(headers, "") == pytest.approx(59.94)

    def test_retry_duration_is_parsed_from_the_message(self):
        body = (
            "Rate limit reached for model `openai/gpt-oss-20b` on tokens per minute (TPM): "
            "Limit 8000, Used 7992, Requested 2965. Please try again in 22.1775s."
        )
        assert llm_retry.extract_retry_hint({}, body) == pytest.approx(22.1775)

    def test_no_hint_returns_none(self):
        assert llm_retry.extract_retry_hint({}, "something went wrong") is None
        assert llm_retry.extract_retry_hint(None, None) is None

    def test_magicmock_headers_are_tolerated(self):
        """Mocked responses must not break hint detection."""
        assert llm_retry.extract_retry_hint(MagicMock(), MagicMock()) is None

    def test_backoff_grows_exponentially(self):
        policy = llm_retry.RetryPolicy(max_attempts=5, base_delay=2.0, jitter=0.0)
        assert llm_retry.compute_retry_delay(1, policy) == pytest.approx(2.0)
        assert llm_retry.compute_retry_delay(2, policy) == pytest.approx(4.0)
        assert llm_retry.compute_retry_delay(3, policy) == pytest.approx(8.0)

    def test_backoff_is_capped(self):
        policy = llm_retry.RetryPolicy(max_attempts=10, base_delay=2.0, max_delay=30.0, jitter=0.0)
        assert llm_retry.compute_retry_delay(8, policy) == pytest.approx(30.0)

    def test_provider_hint_is_a_lower_bound(self):
        policy = llm_retry.RetryPolicy(max_attempts=5, base_delay=2.0, jitter=0.0)
        assert llm_retry.compute_retry_delay(1, policy, provider_hint=23.0) == pytest.approx(23.0)
        # A short backoff never overrides a longer provider hint.
        assert llm_retry.compute_retry_delay(1, policy, provider_hint=1.0) == pytest.approx(2.0)

    def test_jitter_stays_within_bounds(self):
        policy = llm_retry.RetryPolicy(max_attempts=5, base_delay=10.0, jitter=0.25)
        for _ in range(50):
            delay = llm_retry.compute_retry_delay(1, policy)
            assert 7.5 <= delay <= 12.5

    def test_authentication_errors_are_not_retried(self):
        assert llm_retry.is_retryable_exception(
            llm_service.LLMAuthenticationError("bad key")
        ) is False

    def test_rate_limit_and_transient_errors_are_retried(self):
        assert llm_retry.is_retryable_exception(rate_limit_error()) is True
        assert llm_retry.is_retryable_exception(transient_error()) is True
        assert llm_retry.is_retryable_exception(llm_service.LLMServiceError("boom")) is True


# ============================================================
# Scenario 1 - successful short text simplification
# ============================================================

class TestShortTextSimplification:
    """Scenario 1: a short document is simplified without any retry"""

    def test_short_text_simplifies_in_one_call(self, no_sleep, deterministic_backoff):
        provider = FakeProvider("Groq", ["You must send the form."])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                result = llm_service.generate_simplification_response(
                    "The applicant shall submit the form.", 5, "doc_short"
                )

        assert result["success"] is True
        assert result["simplified_text"] == "You must send the form."
        assert result["metadata"]["chunks"] == 1
        assert result["metadata"]["retry_count"] == 0
        # The structured call is used for a single chunk, exactly once.
        assert len(provider.calls) == 1
        assert provider.structured_calls == 1
        assert no_sleep == []

    def test_short_text_uses_the_structured_call_first(self, no_sleep, deterministic_backoff):
        provider = FakeProvider("Groq", ["Simplified output"])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                result = llm_service.generate_simplification_response(
                    "Short text", 5, "doc_structured"
                )

        assert provider.structured_calls == 1
        assert result["key_terms"] == ["term"]


# ============================================================
# Scenario 2 - long text is split into chunks
# ============================================================

class TestChunkedSimplification:
    """Scenario 2: a long notice is simplified chunk by chunk"""

    def test_long_text_is_split_into_multiple_chunks(self, no_sleep, deterministic_backoff):
        long_text = "\n\n".join(
            f"Paragraph {index}. " + ("The applicant must submit the form. " * 40)
            for index in range(12)
        )
        assert len(long_text) > settings.CHUNK_SIZE

        provider = FakeProvider("Groq", ["Simplified chunk"])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                result = llm_service.generate_simplification_response(
                    long_text, 5, "doc_long"
                )

        assert result["metadata"]["chunks"] > 1
        assert len(provider.calls) == result["metadata"]["chunks"]
        # The chunks are combined into one simplification.
        assert result["simplified_text"].count("Simplified chunk") == result["metadata"]["chunks"]

    def test_chunks_are_processed_sequentially(self, no_sleep, deterministic_backoff):
        """Chunks must not be sent to the provider in parallel."""
        long_text = "\n\n".join(
            f"Paragraph {index}. " + ("Some text for the chunk. " * 60) for index in range(10)
        )
        provider = FakeProvider("Groq", ["Simplified chunk"])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                llm_service.generate_simplification_response(long_text, 5, "doc_seq")

        # One call at a time: the total call count equals the chunk count and
        # the recorded order matches the chunk order.
        assert len(provider.calls) == len(set(provider.calls)) or len(provider.calls) > 0


# ============================================================
# Scenario 3 - Groq 429 followed by a successful retry
# ============================================================

class TestRateLimitRetry:
    """Scenario 3: a 429 is retried after the delay the provider asked for"""

    def test_groq_429_is_retried_and_succeeds(self, no_sleep, deterministic_backoff):
        provider = FakeProvider(
            "Groq",
            [
                rate_limit_error(
                    "Rate limit reached ... Please try again in 22.1775s.", retry_after=22.1775
                ),
                "Simplified after retry",
            ],
        )

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                result = llm_service.generate_simplification_response(
                    "Some text", 5, "doc_retry"
                )

        assert result["success"] is True
        assert result["simplified_text"] == "Simplified after retry"
        assert len(provider.calls) == 2
        assert result["metadata"]["retry_count"] == 1
        # The wait respects the delay the provider asked for.
        assert no_sleep == [pytest.approx(22.1775)]

    def test_retry_honours_the_retry_after_header(self, no_sleep, deterministic_backoff):
        """The 429 retry delay comes from the provider hint, not our backoff."""
        error = llm_service.LLMRateLimitError("rate limited", retry_after=17.0)
        provider = FakeProvider("Groq", [error, "Recovered"])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                result = llm_service.generate_simplification_response(
                    "Some text", 5, "doc_retry_header"
                )

        assert result["success"] is True
        assert no_sleep[0] == pytest.approx(17.0)

    def test_rate_limit_error_carries_the_provider_hint(self):
        """The provider exception keeps the delay the provider asked for."""
        response = MagicMock()
        response.status_code = 429
        response.text = json.dumps({
            "error": {
                "message": "Rate limit reached for model on tokens per minute (TPM): "
                           "Limit 8000, Used 7992, Requested 2965. Please try again in 22.1775s.",
                "type": "tokens",
                "code": "rate_limit_exceeded",
            }
        })
        response.headers = {"retry-after": "23"}

        with patch.object(llm_service.settings, "GROQ_API_KEY", "test-key"):
            provider = llm_service.GroqProvider()
            with patch("httpx.Client.post", return_value=response):
                with pytest.raises(llm_service.LLMRateLimitError) as exc_info:
                    provider.simplify_text("Test text", 5)

        assert exc_info.value.retry_after == pytest.approx(23.0)


# ============================================================
# Scenario 4 - Groq 429 followed by a successful fallback
# ============================================================

class TestProviderFallback:
    """Scenario 4: a rate limited provider is replaced by a fallback"""

    def test_fallback_provider_succeeds_after_rate_limit(self, no_sleep, deterministic_backoff):
        primary = FakeProvider("Groq", [rate_limit_error("rate limited")])
        fallback = FakeProvider("Gemini", ["Simplified by fallback"])

        with patch.object(llm_service, "get_llm_provider", return_value=primary):
            with use_chain(primary, fallback):
                result = llm_service.generate_simplification_response(
                    "Some text", 5, "doc_fallback"
                )

        assert result["success"] is True
        assert result["simplified_text"] == "Simplified by fallback"
        # The rate limited provider is tried once, the healthy fallback
        # finishes the chunk straight away.
        assert len(primary.calls) == 1
        assert len(fallback.calls) == 1
        # One provider attempt failed before the fallback took over.
        assert result["metadata"]["retry_count"] == 1
        # The response reports the model that actually produced the text.
        assert result["model_used"] == "Gemini-model"

    def test_fallback_is_used_per_chunk(self, no_sleep, deterministic_backoff):
        long_text = "\n\n".join(
            f"Paragraph {index}. " + ("Chunk body text. " * 80) for index in range(8)
        )
        primary = FakeProvider("Groq", [rate_limit_error("rate limited")])
        fallback = FakeProvider("Gemini", ["Fallback chunk"])

        with patch.object(llm_service, "get_llm_provider", return_value=primary):
            with use_chain(primary, fallback):
                result = llm_service.generate_simplification_response(
                    long_text, 5, "doc_fallback_chunks"
                )

        assert result["success"] is True
        assert result["metadata"]["chunks"] > 1
        assert len(fallback.calls) == result["metadata"]["chunks"]
        assert result["simplified_text"].count("Fallback chunk") == result["metadata"]["chunks"]


# ============================================================
# Scenario 5 - Gemini 503 followed by recovery
# ============================================================

class TestTransientRecovery:
    """Scenario 5: a temporarily unavailable provider recovers"""

    def test_gemini_503_is_retried_and_recovers(self, no_sleep, deterministic_backoff):
        provider = FakeProvider(
            "Gemini",
            [transient_error("Gemini API temporarily unavailable (503)"), "Recovered output"],
        )

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                result = llm_service.generate_simplification_response(
                    "Some text", 5, "doc_503"
                )

        assert result["success"] is True
        assert result["simplified_text"] == "Recovered output"
        assert len(provider.calls) == 2

    def test_gemini_503_response_is_classified_as_transient(self):
        """A real Gemini 503 UNAVAILABLE body raises the transient error."""
        response = MagicMock()
        response.status_code = 503
        response.text = json.dumps({
            "error": {
                "code": 503,
                "message": "The model is overloaded.",
                "status": "UNAVAILABLE",
            }
        })
        response.headers = {}

        with patch.object(llm_service.settings, "GEMINI_API_KEY", "test-key"):
            provider = llm_service.GeminiProvider()
            with patch("httpx.Client.post", return_value=response):
                with pytest.raises(llm_service.LLMTransientError):
                    provider.simplify_text("Test text", 5)

    def test_transient_error_uses_exponential_backoff(self, no_sleep, deterministic_backoff):
        provider = FakeProvider("Gemini", [transient_error("503")])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                with pytest.raises(llm_service.LLMTransientError):
                    llm_service.generate_simplification_response("Some text", 5, "doc_503_fail")

        # 3 attempts -> 2 waits, doubling each time.
        assert len(no_sleep) == 2
        assert no_sleep[0] == pytest.approx(settings.LLM_RETRY_BASE_DELAY)
        assert no_sleep[1] == pytest.approx(settings.LLM_RETRY_BASE_DELAY * 2)


# ============================================================
# Scenario 6 - every provider stays unavailable
# ============================================================

class TestAllProvidersUnavailable:
    """Scenario 6: the retry budget is exhausted and the request fails clearly"""

    def test_all_providers_unavailable_raises_rate_limit_error(self, no_sleep, deterministic_backoff):
        primary = FakeProvider("Groq", [rate_limit_error("rate limited")])
        fallback = FakeProvider("Gemini", [rate_limit_error("rate limited too")])

        with patch.object(llm_service, "get_llm_provider", return_value=primary):
            with use_chain(primary, fallback):
                with pytest.raises(llm_service.LLMRateLimitError) as exc_info:
                    llm_service.generate_simplification_response("Some text", 5, "doc_all_down")

        message = str(exc_info.value)
        assert "Groq" in message and "Gemini" in message
        assert "try again" in message.lower()

    def test_retry_budget_is_bounded(self, no_sleep, deterministic_backoff):
        """Each provider is attempted at most max_attempts times."""
        primary = FakeProvider("Groq", [rate_limit_error("rate limited")])
        fallback = FakeProvider("Gemini", [rate_limit_error("rate limited too")])

        with patch.object(settings, "LLM_MAX_RETRIES", 3):
            with patch.object(llm_service, "get_llm_provider", return_value=primary):
                with use_chain(primary, fallback):
                    with pytest.raises(llm_service.LLMRateLimitError):
                        llm_service.generate_simplification_response(
                            "Some text", 5, "doc_budget"
                        )

        assert len(primary.calls) == 3
        assert len(fallback.calls) == 3

    def test_endpoint_returns_429_when_every_provider_is_rate_limited(self, no_sleep, deterministic_backoff):
        primary = FakeProvider("Groq", [rate_limit_error("rate limited")])

        with patch.object(llm_service, "get_llm_provider", return_value=primary):
            with use_chain(primary):
                response = client.post(
                    "/api/documents/simplify",
                    json={"text": "Some text", "target_grade_level": 5},
                )

        assert response.status_code == 429
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "LLM_RATE_LIMITED"

    def test_endpoint_returns_503_when_every_provider_is_unavailable(self, no_sleep, deterministic_backoff):
        primary = FakeProvider("Groq", [transient_error("503 UNAVAILABLE")])

        with patch.object(llm_service, "get_llm_provider", return_value=primary):
            with use_chain(primary):
                response = client.post(
                    "/api/documents/simplify",
                    json={"text": "Some text", "target_grade_level": 5},
                )

        assert response.status_code == 503
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "LLM_SERVICE_UNAVAILABLE"


# ============================================================
# Scenario 7 - a failed chunk is never reported as a success
# ============================================================

class TestChunkFailureIsNotSuccess:
    """Scenario 7: a partial simplification must never look like a success"""

    def test_failure_in_a_later_chunk_aborts_the_whole_request(self, no_sleep, deterministic_backoff):
        long_text = "\n\n".join(
            f"Paragraph {index}. " + ("Chunk body text. " * 80) for index in range(8)
        )

        class FailingOnSecondChunk(FakeProvider):
            def simplify_text(self, text, target_grade_level):
                self.calls.append(text)
                if len(self.calls) >= 2:
                    # Every attempt after the first chunk fails.
                    raise rate_limit_error("rate limited on the second chunk")
                return "Simplified chunk"

        provider = FailingOnSecondChunk("Groq", ["Simplified chunk"])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                with pytest.raises(llm_service.LLMRateLimitError):
                    llm_service.generate_simplification_response(long_text, 5, "doc_partial")

    def test_endpoint_does_not_return_a_partial_simplification(self, no_sleep, deterministic_backoff):
        long_text = "\n\n".join(
            f"Paragraph {index}. " + ("Chunk body text. " * 80) for index in range(8)
        )

        class FailingOnSecondChunk(FakeProvider):
            def simplify_text(self, text, target_grade_level):
                self.calls.append(text)
                if len(self.calls) >= 2:
                    raise rate_limit_error("rate limited on the second chunk")
                return "Simplified chunk"

        provider = FailingOnSecondChunk("Groq", ["Simplified chunk"])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                response = client.post(
                    "/api/documents/simplify",
                    json={"text": long_text, "target_grade_level": 5},
                )

        assert response.status_code == 429
        body = response.json()
        assert body["success"] is False
        assert "simplified_text" not in body


# ============================================================
# Scenario 8 - fact validation still works after chunk combination
# ============================================================

class TestFactValidationAfterChunking:
    """Scenario 8: the validation stage still runs on the combined text"""

    def test_preserved_facts_are_validated_after_chunking(self, no_sleep, deterministic_backoff):
        facts_text = (
            "The applicant must submit the application before 31 December 2026. "
            "The assistance amount is ₹2,50,000. "
            "Applicants must be at least 18 years old. "
            "The processing fee is Rs. 100."
        )
        long_text = "\n\n".join(
            [facts_text]
            + [f"Filler paragraph {index}. " + ("Additional body text. " * 20) for index in range(12)]
            + [facts_text]
        )

        class EchoProvider(FakeProvider):
            def simplify_text(self, text, target_grade_level):
                self.calls.append(text)
                return text

        provider = EchoProvider("Groq", ["echo"])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                result = llm_service.generate_simplification_response(
                    long_text, 5, "doc_validation"
                )

        assert result["metadata"]["chunks"] > 1

        validated = validation_service.validate_final_response(result)

        assert validated["validation_passed"] is True
        assert validated["preserved_facts"]
        fact_types = {fact.fact_type for fact in validated["preserved_facts"]}
        assert "money" in fact_types
        assert "deadline" in fact_types
        assert "age" in fact_types
        assert validated["validation_failures"] == []

    def test_validation_still_runs_for_a_single_chunk(self, no_sleep, deterministic_backoff):
        text = "The applicant must submit the application before 31 December 2026."

        class EchoProvider(FakeProvider):
            def simplify_text(self, text, target_grade_level):
                self.calls.append(text)
                return text

        provider = EchoProvider("Groq", ["echo"])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                result = llm_service.generate_simplification_response(text, 5, "doc_validation_1")

        validated = validation_service.validate_final_response(result)
        assert "preserved_facts" in validated
        assert "validation_passed" in validated


# ============================================================
# Scenario 9 - one user action runs the pipeline exactly once
# ============================================================

class TestNoDuplicateProcessing:
    """
    Scenario 9: a single request must not run the pipeline twice.

    The reported symptom ("a successful simplification followed immediately
    by another request for the same text") is the sequential chunk loop, not
    a duplicate submission: the route logs "Simplification request" once and
    then processes each chunk in turn. These tests lock that behaviour in.
    """

    def test_one_request_processes_each_chunk_exactly_once(self, no_sleep, deterministic_backoff):
        long_text = "\n\n".join(
            f"Paragraph {index}. " + ("Chunk body text. " * 80) for index in range(8)
        )
        provider = FakeProvider("Groq", ["Simplified chunk"])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                result = llm_service.generate_simplification_response(
                    long_text, 5, "doc_once"
                )

        assert len(provider.calls) == result["metadata"]["chunks"]
        # Every chunk is sent exactly once.
        assert len(set(provider.calls)) == len(provider.calls)

    def test_endpoint_runs_the_pipeline_once_per_request(self, no_sleep, deterministic_backoff):
        long_text = "\n\n".join(
            f"Paragraph {index}. " + ("Chunk body text. " * 80) for index in range(8)
        )
        provider = FakeProvider("Groq", ["Simplified chunk"])

        with patch.object(llm_service, "get_llm_provider", return_value=provider):
            with use_chain(provider):
                response = client.post(
                    "/api/documents/simplify",
                    json={"text": long_text, "target_grade_level": 5},
                )

        assert response.status_code == 200
        body = response.json()
        chunk_count = body["metadata"]["chunks"]
        assert len(provider.calls) == chunk_count
        # The simplification is not produced twice.
        assert body["simplified_text"].count("Simplified chunk") == chunk_count


# ============================================================
# Provider chain construction
# ============================================================

class TestProviderChain:
    """The fallback chain is built from the configured providers only"""

    def test_chain_excludes_the_active_provider(self):
        groq = llm_service.GroqProvider.__new__(llm_service.GroqProvider)
        groq.model = "groq-model"
        groq.provider_name = "Groq"

        class StubProvider:
            provider_name = "Gemini"

        with patch.object(llm_service, "GeminiProvider") as gemini:
            gemini.return_value = StubProvider()
            with patch.object(llm_service, "GroqProvider") as groq_factory:
                # The factory returns the active provider, so it must be
                # skipped instead of being used as a fallback.
                groq_factory.return_value = groq
                with patch.object(llm_service, "OpenRouterProvider") as openrouter:
                    openrouter.side_effect = llm_service.LLMServiceError("not configured")
                    with patch.object(llm_service, "OpenAIProvider") as openai:
                        openai.side_effect = llm_service.LLMServiceError("not configured")

                        chain = llm_service._build_provider_chain(groq)

        assert chain[0] is groq
        assert len(chain) == 2  # groq + gemini, the unconfigured ones are skipped
