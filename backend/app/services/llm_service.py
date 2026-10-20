"""
LLM Service for text simplification.
Handles LLM provider abstraction, prompt engineering, and structured output generation.
"""

import json
import time
import logging
import asyncio
import threading
from typing import Dict, List, Any, Optional, Tuple
import re
from datetime import datetime

import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.simplification import SimplificationResponse
from app.services import llm_retry
from app.services.text_fidelity import strip_document_artifacts

logger = get_logger(__name__)


class LLMServiceError(Exception):
    """Base exception for LLM service errors"""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        # Number of seconds the provider asked us to wait before retrying.
        self.retry_after = retry_after


class LLMQuotaExhaustedError(LLMServiceError):
    """Exception raised when API quota is exhausted"""
    pass


class LLMAuthenticationError(LLMServiceError):
    """Exception raised for authentication/authorization errors"""
    pass


class LLMRateLimitError(LLMServiceError):
    """Exception raised for rate limit errors (temporary)"""
    pass


class LLMTransientError(LLMServiceError):
    """
    Exception raised when a provider is temporarily unavailable.

    Covers HTTP 5xx responses and "overloaded" style errors (for example
    Gemini answering ``503 UNAVAILABLE``). These are worth retrying with a
    backoff, unlike authentication failures which are permanent.
    """
    pass


def _response_text(response: Any) -> str:
    """Returns the response body as text, tolerating non-string mock bodies."""
    text = getattr(response, "text", None)
    return text if isinstance(text, str) else ""


def _response_headers(response: Any) -> Any:
    """Returns the response headers, tolerating mocked responses."""
    return getattr(response, "headers", None)


class LLMProvider:
    """Abstract base class for LLM providers"""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS

        if not self.api_key:
            raise LLMServiceError("LLM API key not configured. Please set LLM_API_KEY in environment variables.")

    def simplify_text(self, text: str, target_grade_level: int) -> str:
        """
        Simplify text using LLM.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Simplified text

        Raises:
            LLMServiceError: If simplification fails
        """
        raise NotImplementedError("Subclasses must implement simplify_text")

    def generate_structured_simplification(self, text: str, target_grade_level: int) -> Dict[str, Any]:
        """
        Generate structured simplification with metadata.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Dictionary with structured simplification data

        Raises:
            LLMServiceError: If simplification fails
        """
        raise NotImplementedError("Subclasses must implement generate_structured_simplification")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for simplification"""
        return """You are a government document simplification assistant. Your task is to simplify complex government document text to make it more accessible while preserving all critical factual information.

CRITICAL RULES:
1. NEVER invent new information or facts.
2. NEVER change numbers, dates, deadlines, monetary amounts, percentages, ages, or quantities.
3. NEVER remove eligibility requirements, required documents, or important conditions.
4. ALWAYS preserve the original meaning completely.
5. If a technical or legal term cannot be simplified, keep it but add a brief explanation.
6. Do not provide legal advice or interpret ambiguous legal language as fact.
7. If the source text is unclear, preserve the uncertainty instead of guessing.
8. IGNORE document artifacts. Page numbers, page markers (such as "Page 4 of 7" or "--- Page 3 ---"), running headers, footers and page-break text are NOT content. Never repeat them and never turn them into an instruction, a step or a requirement.
9. NEVER add anything the source does not state. Do not invent steps, headings, procedures, documents, deadlines, amounts, contacts or conditions. If the source does not mention something, leave it out.
10. KEEP the certainty of the source. Words such as "normally", "usually", "generally", "in principle", "as far as possible", "expected to", "may", "subject to", "provided that", "only if" and "except" carry legal meaning. Never drop them and never turn them into "will", "must" or "always".
11. Do not change the kind of organisation. If the source says "university", "college" or "institute", keep that exact word - never replace it with "school", and never replace "school" with "college".
12. NEVER turn a statement about the document into a statement about what the reader must do. "It is declared in the application" stays about the application, and must not become "you must declare it in section 4 of the form".

COMPLETENESS - THIS MATTERS MOST:
- Simplify the WHOLE document. Every section, paragraph and list of the source must appear in the output.
- Never shorten the document into a summary, never skip a section, and never stop before the end of the source.
- Keep the sections of the source in the same order.
- Do not turn eligibility rules into procedure steps, or procedure steps into eligibility rules, only to make the output look organised.
- Keep instructions for applicants and instructions for institutions separate, and make clear who each instruction is for.

SIMPLIFICATION GUIDELINES:
1. Break long sentences into shorter, clearer sentences.
2. Replace unnecessarily complex words with simpler synonyms when meaning remains unchanged.
3. Use active voice where it improves clarity.
4. Use clear, meaningful headings and subheadings so the reader can follow the document. A heading may name something the source describes, but it must never introduce a requirement, a step or a fact that the source does not state.
5. Keep paragraphs short and focused on a single topic, and use bullet or numbered lists when the source lists several things.
6. Use second-person ("you") when referring to the reader/applicant, but only for what the source actually requires.
7. Aim for reading grade level specified by the user.

DOCUMENT STRUCTURE:
- Keep the order of the source document. Do not move sections around.
- Do not turn eligibility rules into procedure steps, or procedure steps into eligibility rules, only to make the output look organised.
- Keep instructions for applicants and instructions for institutions separate, and make clear who each instruction is for.
- Keep the headings of the source as the headings of the simplified text wherever possible.

FORMAT INSTRUCTIONS:
- Return only the simplified text without commentary.
- Preserve all important factual information exactly as it appears.
- Keep every condition, exception, qualifier and obligation from the source.
- Use Markdown for headings (###), bold (**text**) and lists (- or 1.) where they help the reader.
- Use clear, plain language appropriate for the target grade level."""

    def _raise_provider_error(self, response: Any, provider_name: str) -> None:
        """
        Raises the exception that matches an OpenAI-compatible error response.

        Groq, OpenAI and OpenRouter share the same response shape:

        * HTTP 429 - the request was throttled (per-minute token or request
          limits). The provider usually says how long to wait, which is read
          from the ``Retry-After`` / ``x-ratelimit-reset-tokens`` headers or
          from the error message.
        * HTTP 401/403 - the credentials are wrong. Permanent, never retried.
        * HTTP 5xx - the provider is temporarily unavailable. Worth a short
          backoff before the next attempt.

        This method always raises.
        """
        status_code = getattr(response, "status_code", 0)
        body = _response_text(response)
        retry_after = llm_retry.extract_retry_hint(_response_headers(response), body)
        error_msg = f"{provider_name} API error ({status_code}): {body}"
        logger.error(error_msg)

        if status_code == 429:
            lowered = body.lower()
            if "rate limit" in lowered or "tokens per minute" in lowered:
                raise LLMRateLimitError(error_msg, retry_after=retry_after)
            raise LLMQuotaExhaustedError(error_msg, retry_after=retry_after)
        if status_code in (401, 403):
            raise LLMAuthenticationError(error_msg)
        if status_code in (500, 502, 503, 504):
            raise LLMTransientError(error_msg, retry_after=retry_after)
        raise LLMServiceError(error_msg, retry_after=retry_after)

    def _require_text(self, text: str, provider_name: str) -> str:
        """
        Treats an empty completion as a failure.

        A reasoning model can spend its whole output budget on internal
        reasoning and return an empty answer. Returning that as a successful
        simplification would silently drop the document, so it is raised as an
        error and the retry policy can act on it.
        """
        cleaned = (text or "").strip()
        if not cleaned:
            error_msg = (
                f"{provider_name} returned an empty completion. The model may have used "
                "its whole output budget while reasoning."
            )
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        return cleaned

    def _build_simplification_prompt(self, text: str, target_grade_level: int) -> str:
        """Build the user prompt for simplification"""
        return f"""Simplify the following government document text to a reading grade level of {target_grade_level} while preserving all critical factual information.

CRITICAL INFORMATION TO PRESERVE EXACTLY:
- All dates, deadlines, and time frames
- All monetary amounts (especially ₹ amounts)
- All percentages
- All ages and age requirements
- All quantities and numerical values
- All eligibility requirements
- All required documents
- All important conditions and exceptions
- All qualifiers of certainty (such as "normally", "usually", "in principle", "as far as possible", "expected to", "may")
- All conditional phrases (such as "subject to", "provided that", "only if", "except", "at the discretion of")
- All contact information (if present)
- All organization and scheme names
- The exact kind of organisation mentioned (university, college, institute, school, ministry, department, board, authority)

IMPORTANT: Do not change any numbers, dates, or factual information. Do not remove or upgrade any qualifier, condition or exception. Do not add any instruction, step or requirement that the text does not state. Keep the order of the source document, and keep instructions for applicants separate from instructions for institutions.

DOCUMENT ARTIFACTS: any page number, page marker (for example "Page 4 of 7"), header, footer or page-break text in the text below is a printing artifact and not content. Leave it out completely. Never turn it into an instruction or a step.

Original text:
```
{text}
```

Simplified text (grade level {target_grade_level}):"""

    def _build_structured_simplification_prompt(self, text: str, target_grade_level: int) -> str:
        """Build the user prompt for structured simplification"""
        return f"""Simplify the following government document text to a reading grade level of {target_grade_level} while preserving all critical factual information.

CRITICAL INFORMATION TO PRESERVE EXACTLY:
- All dates, deadlines, and time frames
- All monetary amounts (especially ₹ amounts)
- All percentages
- All ages and age requirements
- All quantities and numerical values
- All eligibility requirements
- All required documents
- All important conditions and exceptions
- All qualifiers of certainty (such as "normally", "usually", "in principle", "as far as possible", "expected to", "may")
- All conditional phrases (such as "subject to", "provided that", "only if", "except", "at the discretion of")
- All contact information (if present)
- All organization and scheme names
- The exact kind of organisation mentioned (university, college, institute, school, ministry, department, board, authority)

IMPORTANT: Do not change any numbers, dates, or factual information. Do not remove or upgrade any qualifier, condition or exception. Do not add any instruction, step or requirement that the text does not state. Keep the order of the source document, and keep instructions for applicants separate from instructions for institutions.

DOCUMENT ARTIFACTS: any page number, page marker (for example "Page 4 of 7"), header, footer or page-break text in the text below is a printing artifact and not content. Leave it out completely. Never turn it into an instruction or a step.

Original text:
```
{text}
```

Return a JSON object with the following structure:
{{
    "simplified_text": "The simplified text goes here...",
    "key_terms": ["list", "of", "important", "terms", "preserved"],
    "sections": [
        {{
            "title": "Optional section title",
            "original_text": "Original section text",
            "simplified_text": "Simplified section text",
            "grade_level_improvement": 3
        }}
    ]
}}

Only include sections if the text naturally divides into distinct parts. The simplified_text field must contain the full simplified text.

Simplified text (grade level {target_grade_level}):"""


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible API provider (OpenAI, Azure OpenAI, etc.)"""

    provider_name = "OpenAI"

    def __init__(self, base_url: Optional[str] = None):
        super().__init__()
        self.base_url = base_url or "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def simplify_text(self, text: str, target_grade_level: int) -> str:
        """
        Simplify text using OpenAI API.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Simplified text

        Raises:
            LLMServiceError: If API call fails
        """
        prompt = self._build_simplification_prompt(text, target_grade_level)

        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )

                if response.status_code != 200:
                    # Handle specific error types (rate limit, auth, transient)
                    self._raise_provider_error(response, "OpenAI")

                result = response.json()
                simplified_text = self._require_text(
                    result["choices"][0]["message"]["content"], "OpenAI"
                )

                logger.info(f"OpenAI simplification successful (tokens: {result['usage']['total_tokens']})")
                return simplified_text

        except httpx.TimeoutException:
            error_msg = "OpenAI API timeout"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"OpenAI API request failed: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError, LLMTransientError):
            # Re-raise specific error types without wrapping
            raise
        except Exception as e:
            error_msg = f"Unexpected error in OpenAI simplification: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)

    def generate_structured_simplification(self, text: str, target_grade_level: int) -> Dict[str, Any]:
        """
        Generate structured simplification using OpenAI's JSON mode.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Dictionary with structured simplification data

        Raises:
            LLMServiceError: If API call fails
        """
        prompt = self._build_structured_simplification_prompt(text, target_grade_level)

        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"}
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )

                if response.status_code != 200:
                    # Handle specific error types (rate limit, auth, transient)
                    self._raise_provider_error(response, "OpenAI")

                result = response.json()
                response_text = self._require_text(
                    result["choices"][0]["message"]["content"], "OpenAI"
                )

                try:
                    structured_result = json.loads(response_text)

                    # Ensure required fields
                    structured_result.setdefault("simplified_text", "")
                    structured_result.setdefault("key_terms", [])
                    structured_result.setdefault("sections", [])

                    logger.info(f"OpenAI structured simplification successful (tokens: {result['usage']['total_tokens']})")
                    return structured_result

                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse OpenAI JSON response: {str(e)}"
                    logger.error(error_msg)
                    # Fall back to regular simplification
                    simplified_text = self.simplify_text(text, target_grade_level)
                    return {
                        "simplified_text": simplified_text,
                        "key_terms": [],
                        "sections": []
                    }

        except httpx.TimeoutException:
            error_msg = "OpenAI API timeout"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError, LLMTransientError):
            # Re-raise specific error types without wrapping
            raise
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError, LLMTransientError):
            # Re-raise specific error types without wrapping
            raise
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError, LLMTransientError):
            # Re-raise specific error types without wrapping
            raise
        except Exception as e:
            error_msg = f"Error in structured OpenRouter simplification: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)


class MockProvider(LLMProvider):
    """Mock provider for testing without real API calls"""

    provider_name = "Mock"

    def __init__(self):
        # Don't call super().__init__() as it requires API key
        # Mock provider doesn't need API key validation
        self.api_key = "mock-key-for-testing"
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS

    def simplify_text(self, text: str, target_grade_level: int) -> str:
        """
        Mock simplification for testing.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Mock simplified text
        """
        logger.info(f"Mock simplification for text of length {len(text)}")

        # Simple mock simplification logic
        simplified = text

        # Replace complex words with simpler ones
        replacements = {
            r'\bshall\b': 'must',
            r'\bshall\s+not\b': 'must not',
            r'\bprior\s+to\b': 'before',
            r'\bsubsequent\s+to\b': 'after',
            r'\bapplicant\b': 'you',
            r'\bapplicants\b': 'you',
            r'\bsubmit\b': 'send',
            r'\bduly\s+completed\b': 'filled out',
            r'\brequisite\b': 'required',
            r'\bprescribed\b': 'given',
            r'\beligibility\b': 'who can apply',
            r'\bassistance\s+amount\b': 'money you get',
            r'\bscheme\b': 'program',
        }

        for pattern, replacement in replacements.items():
            simplified = re.sub(pattern, replacement, simplified, flags=re.IGNORECASE)

        # Break long sentences
        sentences = re.split(r'[.!?]+', simplified)
        simplified_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 100:
                # Simple split on commas or conjunctions
                parts = re.split(r',\s+(?:and|or|but)\s+', sentence)
                simplified_sentences.extend([p.strip() for p in parts if p.strip()])
            elif sentence:
                simplified_sentences.append(sentence)

        simplified = '. '.join(simplified_sentences)
        if simplified_sentences:
            simplified += '.'

        return simplified

    def generate_structured_simplification(self, text: str, target_grade_level: int) -> Dict[str, Any]:
        """
        Mock structured simplification for testing.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Mock structured simplification data
        """
        logger.info(f"Mock structured simplification for text of length {len(text)}")

        simplified_text = self.simplify_text(text, target_grade_level)

        return {
            "simplified_text": simplified_text,
            "key_terms": ["applicant", "scheme", "assistance"],
            "sections": [
                {
                    "title": "Application Requirements",
                    "original_text": "Extract the application requirements part",
                    "simplified_text": "What you need to apply",
                    "grade_level_improvement": 4
                }
            ]
        }


class GeminiProvider(LLMProvider):
    """Google Gemini API provider using REST API"""

    provider_name = "Gemini"

    def __init__(self):
        # Use Gemini-specific settings with fallback to legacy settings for backward compatibility
        self.api_key = settings.GEMINI_API_KEY or settings.LLM_API_KEY
        self.model = settings.GEMINI_MODEL or settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

        if not self.api_key:
            raise LLMServiceError("Gemini API key not configured. Please set GEMINI_API_KEY or LLM_API_KEY in environment variables.")

    def _parse_gemini_error(self, status_code: int, error_text: str,
                            retry_after: Optional[float] = None) -> None:
        """
        Parse Gemini API error and raise appropriate exception.

        Args:
            status_code: HTTP status code from Gemini API
            error_text: Response body text from Gemini API
            retry_after: Seconds the provider asked us to wait, if it said so

        Raises:
            LLMQuotaExhaustedError: For 429 RESOURCE_EXHAUSTED quota errors
            LLMAuthenticationError: For 401/403 auth errors
            LLMRateLimitError: For other rate limit errors
            LLMTransientError: For 5xx / temporarily overloaded responses
            LLMServiceError: For other Gemini API errors
        """
        try:
            error_data = json.loads(error_text)
            error_code = error_data.get("error", {}).get("code")
            error_status = error_data.get("error", {}).get("status", "")
            error_msg = error_data.get("error", {}).get("message", "")
        except (json.JSONDecodeError, KeyError, TypeError):
            error_code = status_code
            error_status = ""
            error_msg = error_text

        # Handle quota exhaustion (429 RESOURCE_EXHAUSTED)
        if status_code == 429 and "RESOURCE_EXHAUSTED" in error_status:
            error_detail = f"Gemini API quota exhausted: {error_msg}"
            logger.error(error_detail)
            raise LLMQuotaExhaustedError(error_detail, retry_after=retry_after)

        # Handle authentication errors (401/403)
        if status_code in (401, 403):
            error_detail = f"Gemini API authentication error ({status_code}): {error_msg}"
            logger.error(error_detail)
            raise LLMAuthenticationError(error_detail)

        # Handle other rate limits (429)
        if status_code == 429:
            error_detail = f"Gemini API rate limited: {error_msg}"
            logger.error(error_detail)
            raise LLMRateLimitError(error_detail, retry_after=retry_after)

        # Handle temporarily unavailable / overloaded responses (5xx).
        # Gemini answers "503 UNAVAILABLE" when the model is overloaded; that
        # is transient and is worth a short backoff before the next attempt.
        if status_code in (500, 502, 503, 504) or error_status in (
            "UNAVAILABLE", "INTERNAL", "DEADLINE_EXCEEDED"
        ):
            error_detail = f"Gemini API temporarily unavailable ({status_code}): {error_msg or error_text}"
            logger.error(error_detail)
            raise LLMTransientError(error_detail, retry_after=retry_after)

        # Generic API error
        error_detail = f"Gemini API error ({status_code}): {error_text}"
        logger.error(error_detail)
        raise LLMServiceError(error_detail, retry_after=retry_after)

    def simplify_text(self, text: str, target_grade_level: int) -> str:
        """
        Simplify text using Google Gemini API.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Simplified text

        Raises:
            LLMQuotaExhaustedError: If API quota is exhausted
            LLMAuthenticationError: If authentication fails
            LLMRateLimitError: If rate limited
            LLMServiceError: If API call fails for other reasons
        """
        prompt = self._build_simplification_prompt(text, target_grade_level)

        try:
            # Gemini API endpoint
            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": f"{self._get_system_prompt()}\n\n{prompt}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": self.max_tokens,
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE"
                    }
                ]
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload)

                if response.status_code != 200:
                    # Parse and handle error appropriately
                    retry_after = llm_retry.extract_retry_hint(
                        _response_headers(response), _response_text(response))
                    self._parse_gemini_error(
                        response.status_code,
                        _response_text(response),
                        retry_after=retry_after,
                    )
                    # If we get here, exception was raised above
                    return ""  # Unreachable, but satisfies type checker

                result = response.json()

                # Extract text from Gemini response
                try:
                    simplified_text = self._require_text(
                        result["candidates"][0]["content"]["parts"][0]["text"], "Gemini"
                    )
                    logger.info(f"Gemini simplification successful")
                    return simplified_text
                except (KeyError, IndexError, TypeError) as e:
                    error_msg = f"Failed to parse Gemini response: {str(e)}"
                    logger.error(error_msg)
                    raise LLMServiceError(error_msg)

        except httpx.TimeoutException:
            error_msg = "Gemini API timeout"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Gemini API request failed: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError, LLMTransientError):
            # Re-raise specific error types without wrapping
            raise
        except Exception as e:
            error_msg = f"Unexpected error in Gemini simplification: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)

    def generate_structured_simplification(self, text: str, target_grade_level: int) -> Dict[str, Any]:
        """
        Generate structured simplification using Gemini with JSON output.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Dictionary with structured simplification data

        Raises:
            LLMQuotaExhaustedError: If API quota is exhausted
            LLMAuthenticationError: If authentication fails
            LLMRateLimitError: If rate limited
            LLMServiceError: If API call fails for other reasons
        """
        prompt = self._build_structured_simplification_prompt(text, target_grade_level)

        try:
            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": f"{self._get_system_prompt()}\n\n{prompt}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": self.max_tokens,
                    "responseMimeType": "application/json"
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE"
                    }
                ]
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload)

                if response.status_code != 200:
                    # Parse and handle error appropriately
                    # This will raise the appropriate exception
                    retry_after = llm_retry.extract_retry_hint(
                        _response_headers(response), _response_text(response))
                    self._parse_gemini_error(
                        response.status_code,
                        _response_text(response),
                        retry_after=retry_after,
                    )
                    # If we get here, exception was raised above
                    return {}  # Unreachable, but satisfies type checker

                result = response.json()

                try:
                    response_text = self._require_text(
                        result["candidates"][0]["content"]["parts"][0]["text"], "Gemini"
                    )

                    # Try to parse JSON response
                    try:
                        structured_result = json.loads(response_text)
                        structured_result.setdefault("simplified_text", "")
                        structured_result.setdefault("key_terms", [])
                        structured_result.setdefault("sections", [])

                        logger.info(f"Gemini structured simplification successful")
                        return structured_result

                    except json.JSONDecodeError:
                        # Gemini returned non-JSON when we asked for JSON
                        # This is NOT a quota error, so we can still raise it
                        error_msg = "Gemini returned non-JSON response when JSON was expected"
                        logger.error(error_msg)
                        raise LLMServiceError(error_msg)

                except (KeyError, IndexError, TypeError) as e:
                    error_msg = f"Failed to parse Gemini response: {str(e)}"
                    logger.error(error_msg)
                    raise LLMServiceError(error_msg)

        except httpx.TimeoutException:
            error_msg = "Gemini API timeout"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError, LLMTransientError):
            # Re-raise specific error types without wrapping
            raise
        except Exception as e:
            error_msg = f"Error in Gemini structured simplification: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)


class GroqProvider(LLMProvider):
    """Groq API provider"""

    provider_name = "Groq"

    def __init__(self):
        # Use Groq-specific settings
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if not self.api_key:
            raise LLMServiceError("Groq API key not configured. Please set GROQ_API_KEY in environment variables.")

    def _build_payload(self, prompt: str) -> Dict[str, Any]:
        """Builds the request payload for the Groq chat completions API."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        effort = (settings.LLM_REASONING_EFFORT or "").strip().lower()
        if effort and "gpt-oss" in self.model.lower():
            # A reasoning model spends part of max_tokens on internal
            # reasoning, which can leave the answer truncated.
            payload["reasoning_effort"] = effort

        return payload

    def _post(self, payload: Dict[str, Any]) -> Any:
        """
        Sends the request, retrying once without ``reasoning_effort`` when the
        provider does not know that parameter.
        """
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload
            )

            if response.status_code == 400 and "reasoning_effort" in _response_text(response):
                reduced = {key: value for key, value in payload.items() if key != "reasoning_effort"}
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=reduced
                )

            return response

    def simplify_text(self, text: str, target_grade_level: int) -> str:
        """
        Simplify text using Groq API.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Simplified text

        Raises:
            LLMServiceError: If API call fails
        """
        prompt = self._build_simplification_prompt(text, target_grade_level)

        try:
            response = self._post(self._build_payload(prompt))

            if response.status_code != 200:
                # Handle specific error types (rate limit, auth, transient)
                self._raise_provider_error(response, "Groq")

            result = response.json()
            simplified_text = self._require_text(
                result["choices"][0]["message"]["content"], "Groq"
            )

            logger.info(f"Groq simplification successful")
            return simplified_text

        except httpx.TimeoutException:
            error_msg = "Groq API timeout"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Groq API request failed: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError, LLMTransientError):
            # Re-raise specific error types without wrapping
            raise
        except Exception as e:
            error_msg = f"Unexpected error in Groq simplification: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)

    def generate_structured_simplification(self, text: str, target_grade_level: int) -> Dict[str, Any]:
        """
        Generate structured simplification using Groq with JSON mode.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Dictionary with structured simplification data

        Raises:
            LLMServiceError: If API call fails
        """
        prompt = self._build_structured_simplification_prompt(text, target_grade_level)

        try:
            payload = self._build_payload(prompt)
            payload["response_format"] = {"type": "json_object"}

            response = self._post(payload)

            if response.status_code != 200:
                # Handle specific error types (rate limit, auth, transient)
                self._raise_provider_error(response, "Groq")

            result = response.json()
            response_text = self._require_text(
                result["choices"][0]["message"]["content"], "Groq"
            )

            try:
                structured_result = json.loads(response_text)
                structured_result.setdefault("simplified_text", "")
                structured_result.setdefault("key_terms", [])
                structured_result.setdefault("sections", [])

                logger.info(f"Groq structured simplification successful")
                return structured_result

            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse Groq JSON response: {str(e)}"
                logger.error(error_msg)
                # Fall back to regular simplification
                simplified_text = self.simplify_text(text, target_grade_level)
                return {
                    "simplified_text": simplified_text,
                    "key_terms": [],
                    "sections": []
                }

        except httpx.TimeoutException:
            error_msg = "Groq API timeout"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Groq API request failed: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except Exception as e:
            error_msg = f"Error in Groq structured simplification: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider"""

    provider_name = "OpenRouter"

    def __init__(self):
        # Use OpenRouter-specific settings
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Kilo-Org/kilocode",  # Optional, for analytics
            "X-Title": "Cognitive Accessibility Simplifier"  # Optional, for analytics
        }

        if not self.api_key:
            raise LLMServiceError("OpenRouter API key not configured. Please set OPENROUTER_API_KEY in environment variables.")

    def simplify_text(self, text: str, target_grade_level: int) -> str:
        """
        Simplify text using OpenRouter API.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Simplified text

        Raises:
            LLMServiceError: If API call fails
        """
        prompt = self._build_simplification_prompt(text, target_grade_level)

        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )

                if response.status_code != 200:
                    # Handle specific error types (rate limit, auth, transient)
                    self._raise_provider_error(response, "OpenRouter")

                result = response.json()
                simplified_text = self._require_text(
                    result["choices"][0]["message"]["content"], "OpenRouter"
                )

                logger.info(f"OpenRouter simplification successful")
                return simplified_text

        except httpx.TimeoutException:
            error_msg = "OpenRouter API timeout"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"OpenRouter API request failed: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError, LLMTransientError):
            # Re-raise specific error types without wrapping
            raise
        except Exception as e:
            error_msg = f"Unexpected error in OpenRouter simplification: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)

    def generate_structured_simplification(self, text: str, target_grade_level: int) -> Dict[str, Any]:
        """
        Generate structured simplification using OpenRouter with JSON mode.

        Args:
            text: Text to simplify
            target_grade_level: Target reading grade level

        Returns:
            Dictionary with structured simplification data

        Raises:
            LLMServiceError: If API call fails
        """
        prompt = self._build_structured_simplification_prompt(text, target_grade_level)

        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"}
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )

                if response.status_code != 200:
                    # Handle specific error types (rate limit, auth, transient)
                    self._raise_provider_error(response, "OpenRouter")

                result = response.json()
                response_text = self._require_text(
                    result["choices"][0]["message"]["content"], "OpenRouter"
                )

                try:
                    structured_result = json.loads(response_text)
                    structured_result.setdefault("simplified_text", "")
                    structured_result.setdefault("key_terms", [])
                    structured_result.setdefault("sections", [])

                    logger.info(f"OpenRouter structured simplification successful")
                    return structured_result

                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse OpenRouter JSON response: {str(e)}"
                    logger.error(error_msg)
                    # Fall back to regular simplification
                    simplified_text = self.simplify_text(text, target_grade_level)
                    return {
                        "simplified_text": simplified_text,
                        "key_terms": [],
                        "sections": []
                    }

        except httpx.TimeoutException:
            error_msg = "OpenRouter API timeout"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"OpenRouter API request failed: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)
        except Exception as e:
            error_msg = f"Error in OpenRouter structured simplification: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)


def get_llm_provider() -> LLMProvider:
    """
    Get the configured LLM provider with fallback support.

    Returns:
        LLMProvider instance

    Raises:
        LLMServiceError: If provider is not configured or unsupported
    """
    provider = settings.LLM_PROVIDER.lower()
    
    # Handle explicit provider selection
    if provider == "openai":
        return OpenAIProvider()
    elif provider == "gemini":
        return GeminiProvider()
    elif provider == "groq":
        return GroqProvider()
    elif provider == "openrouter":
        return OpenRouterProvider()
    elif provider == "mock":
        return MockProvider()
    elif provider == "auto":
        # Auto mode: try providers in order: Gemini -> Groq -> OpenRouter
        # Skip providers that are not configured
        providers_to_try = []
        
        # Check Gemini
        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            providers_to_try.append(("gemini", GeminiProvider))
        
        # Check Groq
        if hasattr(settings, 'GROQ_API_KEY') and settings.GROQ_API_KEY:
            providers_to_try.append(("groq", GroqProvider))
        
        # Check OpenRouter
        if hasattr(settings, 'OPENROUTER_API_KEY') and settings.OPENROUTER_API_KEY:
            providers_to_try.append(("openrouter", OpenRouterProvider))
        
        # If no providers configured, fall back to mock for testing
        if not providers_to_try:
            logger.warning("No LLM providers configured, falling back to mock provider")
            return MockProvider()
        
        # Try each provider in order
        last_error = None
        for provider_name, provider_class in providers_to_try:
            try:
                logger.info(f"Trying LLM provider: {provider_name}")
                provider_instance = provider_class()
                # Test the provider with a simple call to verify it's working
                # We don't actually make an API call here, just instantiate
                # The actual API calls will happen during simplification
                logger.info(f"Successfully initialized LLM provider: {provider_name}")
                return provider_instance
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_name} provider: {str(e)}")
                last_error = e
                continue
        
        # If all providers failed, raise the last error
        error_msg = f"All configured LLM providers failed. Last error: {str(last_error)}"
        logger.error(error_msg)
        raise LLMServiceError(error_msg)
    else:
        error_msg = f"Unsupported LLM provider: {provider}. Supported providers: openai, gemini, groq, openrouter, mock, auto"
        logger.error(error_msg)
        raise LLMServiceError(error_msg)


def chunk_text_for_simplification(text: str, chunk_size: int = 2000) -> List[str]:
    """
    Split text into chunks for simplification.

    Args:
        text: Text to chunk
        chunk_size: Maximum chunk size in characters

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    paragraphs = re.split(r'\n\s*\n', text)

    current_chunk = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        if len(current_chunk) + len(paragraph) + 2 <= chunk_size:
            current_chunk += paragraph + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # If any chunk is still too large, split by sentences
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= chunk_size:
            final_chunks.append(chunk)
        else:
            # Split by sentences
            sentences = re.split(r'(?<=[.!?])\s+', chunk)
            temp_chunk = ""
            for sentence in sentences:
                if len(temp_chunk) + len(sentence) <= chunk_size:
                    temp_chunk += sentence + " "
                else:
                    if temp_chunk:
                        final_chunks.append(temp_chunk.strip())
                    temp_chunk = sentence + " "
            if temp_chunk:
                final_chunks.append(temp_chunk.strip())

    logger.info(f"Text chunked into {len(final_chunks)} chunks")
    return final_chunks


def _build_retry_policy(max_attempts: Optional[int] = None) -> llm_retry.RetryPolicy:
    """Builds the retry policy from configuration (or an explicit override)."""
    return llm_retry.RetryPolicy(
        max_attempts=(
            max_attempts if max_attempts is not None else settings.LLM_MAX_RETRIES
        ),
        base_delay=settings.LLM_RETRY_BASE_DELAY,
        max_delay=settings.LLM_RETRY_MAX_DELAY,
        jitter=settings.LLM_RETRY_JITTER,
    )


def _run_coroutine_sync(coroutine):
    """
    Runs a coroutine from synchronous code.

    The simplification pipeline is asynchronous so that retry waits use
    ``asyncio.sleep`` instead of blocking a thread. This helper lets the
    synchronous public entry point stay available for callers (and tests)
    that are not running inside an event loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    # A loop is already running in this thread: run the coroutine on a
    # dedicated thread with its own event loop.
    outcome: Dict[str, Any] = {}

    def runner() -> None:
        try:
            outcome["value"] = asyncio.run(coroutine)
        except BaseException as error:  # noqa: BLE001 - re-raised below
            outcome["error"] = error

    worker = threading.Thread(target=runner, daemon=True)
    worker.start()
    worker.join()

    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


def _build_provider_chain(provider: LLMProvider) -> List[LLMProvider]:
    """
    Builds the provider chain: the active provider first, then every other
    configured provider as a fallback.

    Providers that are not configured (missing API key) are skipped. The
    active provider is never repeated in the chain.
    """
    chain: List[LLMProvider] = [provider]
    active_type = type(provider)

    for factory in (GeminiProvider, GroqProvider, OpenRouterProvider, OpenAIProvider):
        try:
            candidate = factory()
        except LLMServiceError:
            # Provider not configured (missing API key), skip it.
            continue
        except Exception:
            # Other instantiation error, skip it.
            continue
        if type(candidate) is active_type:
            continue
        chain.append(candidate)

    return chain


def _provider_label(provider: LLMProvider) -> str:
    """Human readable provider name used in log messages and errors."""
    return getattr(provider, "provider_name", None) or type(provider).__name__


def _build_provider_failure(last_error: BaseException,
                            chain: List[LLMProvider]) -> LLMServiceError:
    """
    Builds a clear, actionable error after every provider failed.

    The original exception type is preserved so the API layer keeps mapping
    the failure to the same status code it always did (429 for rate limits,
    503 for unavailable providers, 500 for everything else).
    """
    tried = ", ".join(_provider_label(provider) for provider in chain)
    message = (
        f"Text simplification failed: every configured provider was unavailable "
        f"(tried: {tried}). Last error: {last_error}. "
        "The service is busy right now - please wait a moment and try again."
    )

    error_class = type(last_error) if isinstance(last_error, LLMServiceError) else LLMServiceError
    return error_class(message, retry_after=getattr(last_error, "retry_after", None))


async def _try_provider(provider: LLMProvider, text: str, target_grade_level: int,
                       prefer_structured: bool) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Makes a single attempt against one provider.

    For a single chunk the structured (JSON) call is attempted first so the
    response can carry key terms and sections. When that fails for a reason
    that is not a provider outage (for example a malformed JSON answer) the
    plain simplification is used instead, which is the previous behaviour.

    A rate limited or unavailable provider is *not* immediately asked again
    with the same large request: the error is propagated so the caller can
    move on to the next provider.
    """
    if prefer_structured:
        try:
            structured = await asyncio.to_thread(
                provider.generate_structured_simplification, text, target_grade_level
            )
            return structured.get("simplified_text", ""), structured
        except LLMAuthenticationError:
            raise
        except (LLMRateLimitError, LLMQuotaExhaustedError, LLMTransientError):
            # The provider is unavailable - a plain call would hit the same
            # limit, so do not spend another request here.
            raise
        except LLMServiceError:
            logger.warning("Structured simplification failed, falling back to regular")

    simplified = await asyncio.to_thread(provider.simplify_text, text, target_grade_level)
    return simplified, None


async def _simplify_with_fallback(text: str, target_grade_level: int,
                                  chain: List[LLMProvider],
                                  policy: llm_retry.RetryPolicy,
                                  deadline: Optional[float],
                                  prefer_structured: bool) -> Tuple[str, Optional[Dict[str, Any]], int, LLMProvider]:
    """
    Simplifies one piece of text, walking the provider chain in rounds.

    Each round gives every configured provider one attempt. If all providers
    fail, the round is repeated after a backoff that respects the delay the
    provider asked for. This keeps a rate limited provider from being
    hammered while still giving it another chance once its quota window has
    recovered, and it lets a healthy fallback provider finish the chunk
    immediately instead of waiting for the primary to recover.

    Returns:
        Tuple of (simplified_text, structured_result_or_None,
        failed_provider_attempts, provider_that_succeeded)
    """
    last_error: Optional[LLMServiceError] = None
    failed_attempts = 0

    for round_index in range(policy.max_attempts):
        round_hint: Optional[float] = None

        for provider in chain:
            try:
                simplified, structured = await _try_provider(
                    provider, text, target_grade_level, prefer_structured
                )
                return simplified, structured, failed_attempts, provider

            except LLMAuthenticationError:
                # Permanent: the credentials are wrong. Never retried.
                raise

            except LLMServiceError as error:
                last_error = error
                failed_attempts += 1
                if not llm_retry.is_retryable_exception(error):
                    raise
                hint = getattr(error, "retry_after", None)
                if hint and (round_hint is None or hint > round_hint):
                    round_hint = hint
                logger.warning(
                    f"{_provider_label(provider)} failed "
                    f"({type(error).__name__}): {error}"
                )

        # Every provider failed in this round.
        if round_index >= policy.max_attempts - 1:
            break

        delay = llm_retry.compute_retry_delay(round_index + 1, policy, round_hint)
        if deadline is not None and time.monotonic() + delay >= deadline:
            logger.warning(
                "The simplification deadline was reached while waiting for a "
                "provider to recover."
            )
            break

        logger.warning(
            f"All {len(chain)} provider(s) failed in round {round_index + 1}/"
            f"{policy.max_attempts}. Retrying in {delay:.1f}s."
        )
        await asyncio.sleep(delay)

    raise _build_provider_failure(
        last_error if last_error else LLMServiceError("No provider was available"), chain
    )


async def _generate_simplification_response_async(text: str, target_grade_level: int,
                                                  document_id: str) -> Dict[str, Any]:
    """
    Generate complete simplification response (asynchronous core).

    Long texts are split into chunks and simplified sequentially, so the
    provider's per-minute token budget is consumed in a predictable order.
    Each chunk is retried with a bounded backoff that respects the delay the
    provider asked for, and falls back to the next configured provider when a
    provider is temporarily unavailable.
    """
    start_time = time.time()
    deadline = time.monotonic() + settings.LLM_SIMPLIFICATION_TIMEOUT

    provider = get_llm_provider()
    policy = _build_retry_policy()

    # Page markers, running headers and footers are printing artifacts, not
    # content. Removing them before the model sees the text is the reliable
    # way to stop a page reference such as "Page 4 of 7" from being turned
    # into an application instruction.
    llm_text, stripped_artifacts = strip_document_artifacts(text)
    if stripped_artifacts:
        logger.info(
            f"Removed {len(stripped_artifacts)} document artifact line(s) before simplification."
        )
    if not llm_text.strip():
        llm_text = text

    chunks = chunk_text_for_simplification(llm_text, settings.CHUNK_SIZE)
    chain = _build_provider_chain(provider)

    key_terms: List[str] = []
    sections: List[Dict[str, Any]] = []
    retry_count = 0
    model_used = provider.model

    if len(chunks) > 1:
        logger.info(f"Processing {len(chunks)} chunks separately")
        simplified_chunks: List[str] = []

        for index, chunk in enumerate(chunks):
            simplified_chunk, _structured, failed_attempts, used_provider = await _simplify_with_fallback(
                chunk, target_grade_level, chain, policy, deadline, prefer_structured=False
            )
            retry_count += failed_attempts
            if used_provider is not provider:
                model_used = used_provider.model
            simplified_chunks.append(simplified_chunk)
            logger.info(
                f"Chunk {index + 1}/{len(chunks)} simplified with "
                f"{_provider_label(used_provider)}."
            )

        simplified_text = "\n\n".join(simplified_chunks)
    else:
        simplified_text, structured, failed_attempts, used_provider = await _simplify_with_fallback(
            llm_text, target_grade_level, chain, policy, deadline, prefer_structured=True
        )
        retry_count += failed_attempts
        if used_provider is not provider:
            model_used = used_provider.model
        if structured:
            key_terms = structured.get("key_terms", [])
            sections = structured.get("sections", [])

    processing_time_ms = int((time.time() - start_time) * 1000)

    return {
        "success": True,
        "document_id": document_id,
        "original_text": text,
        "simplified_text": simplified_text,
        "target_grade_level": target_grade_level,
        "model_used": model_used,
        "processing_time_ms": processing_time_ms,
        "sections": sections,
        "key_terms": key_terms,
        "metadata": {
            "chunks": len(chunks),
            # Number of provider attempts that failed (rate limited,
            # overloaded, ...) before a chunk could be completed.
            "retry_count": retry_count
        }
    }


def simplify_text_with_retry(text: str, target_grade_level: int,
                            max_attempts: int = None) -> Tuple[str, int, str]:
    """
    Simplify text with retry logic.

    Args:
        text: Text to simplify
        target_grade_level: Target reading grade level
        max_attempts: Maximum number of attempts (defaults to config)

    Returns:
        Tuple of (simplified_text, attempts, model_used)

    Raises:
        LLMServiceError: If all attempts fail
    """
    if max_attempts is None:
        max_attempts = settings.MAX_SIMPLIFICATION_ATTEMPTS

    provider = get_llm_provider()
    policy = _build_retry_policy(max_attempts)

    async def _run() -> Tuple[str, int, str]:
        simplified, _structured, failed_attempts, used_provider = await _simplify_with_fallback(
            text, target_grade_level, [provider], policy, None, prefer_structured=False
        )
        return simplified, failed_attempts + 1, used_provider.model

    return _run_coroutine_sync(_run())


def generate_simplification_response(text: str, target_grade_level: int,
                                      document_id: str) -> Dict[str, Any]:
    """
    Generate complete simplification response.

    Args:
        text: Text to simplify
        target_grade_level: Target reading grade level
        document_id: Document identifier

    Returns:
        Dictionary with simplification response data

    Raises:
        LLMServiceError: If simplification fails
    """
    try:
        return _run_coroutine_sync(
            _generate_simplification_response_async(text, target_grade_level, document_id)
        )
    except LLMServiceError:
        raise
    except Exception as e:
        error_msg = f"Unexpected error in simplification pipeline: {str(e)}"
        logger.error(error_msg)
        raise LLMServiceError(error_msg)
