"""
LLM Service for text simplification.
Handles LLM provider abstraction, prompt engineering, and structured output generation.
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
import re
from datetime import datetime

import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.simplification import SimplificationResponse

logger = get_logger(__name__)


class LLMServiceError(Exception):
    """Base exception for LLM service errors"""
    pass


class LLMQuotaExhaustedError(LLMServiceError):
    """Exception raised when API quota is exhausted"""
    pass


class LLMAuthenticationError(LLMServiceError):
    """Exception raised for authentication/authorization errors"""
    pass


class LLMRateLimitError(LLMServiceError):
    """Exception raised for rate limit errors (temporary)"""
    pass


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

SIMPLIFICATION GUIDELINES:
1. Break long sentences into shorter, clearer sentences.
2. Replace unnecessarily complex words with simpler synonyms when meaning remains unchanged.
3. Use active voice where it improves clarity.
4. Add headings and bullet points where appropriate to improve readability.
5. Keep paragraphs focused on a single topic.
6. Use second-person ("you") when referring to the reader/applicant.
7. Aim for reading grade level specified by the user.

FORMAT INSTRUCTIONS:
- Return only the simplified text without commentary.
- Preserve all important factual information exactly as it appears.
- Use clear, plain language appropriate for the target grade level."""

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
- All contact information (if present)
- All organization and scheme names

IMPORTANT: Do not change any numbers, dates, or factual information.

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
- All contact information (if present)
- All organization and scheme names

IMPORTANT: Do not change any numbers, dates, or factual information.

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
                    error_msg = f"OpenAI API error ({response.status_code}): {response.text}"
                    logger.error(error_msg)
                    raise LLMServiceError(error_msg)

                result = response.json()
                simplified_text = result["choices"][0]["message"]["content"].strip()

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
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError):
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
                    error_msg = f"OpenAI API error ({response.status_code}): {response.text}"
                    logger.error(error_msg)
                    raise LLMServiceError(error_msg)

                result = response.json()
                response_text = result["choices"][0]["message"]["content"].strip()

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
        except Exception as e:
            error_msg = f"Error in structured OpenAI simplification: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)


class MockProvider(LLMProvider):
    """Mock provider for testing without real API calls"""

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

    def __init__(self):
        # Use Gemini-specific settings with fallback to legacy settings for backward compatibility
        self.api_key = settings.GEMINI_API_KEY or settings.LLM_API_KEY
        self.model = settings.GEMINI_MODEL or settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

        if not self.api_key:
            raise LLMServiceError("Gemini API key not configured. Please set GEMINI_API_KEY or LLM_API_KEY in environment variables.")

    def _parse_gemini_error(self, status_code: int, error_text: str) -> None:
        """
        Parse Gemini API error and raise appropriate exception.

        Args:
            status_code: HTTP status code from Gemini API
            error_text: Response body text from Gemini API

        Raises:
            LLMQuotaExhaustedError: For 429 RESOURCE_EXHAUSTED quota errors
            LLMAuthenticationError: For 401/403 auth errors
            LLMRateLimitError: For other rate limit errors
            LLMServiceError: For other Gemini API errors
        """
        try:
            error_data = json.loads(error_text)
            error_code = error_data.get("error", {}).get("code")
            error_status = error_data.get("error", {}).get("status", "")
            error_msg = error_data.get("error", {}).get("message", "")
        except (json.JSONDecodeError, KeyError):
            error_code = status_code
            error_status = ""
            error_msg = error_text

        # Handle quota exhaustion (429 RESOURCE_EXHAUSTED)
        if status_code == 429 and "RESOURCE_EXHAUSTED" in error_status:
            error_detail = f"Gemini API quota exhausted: {error_msg}"
            logger.error(error_detail)
            raise LLMQuotaExhaustedError(error_detail)

        # Handle authentication errors (401/403)
        if status_code in (401, 403):
            error_detail = f"Gemini API authentication error ({status_code}): {error_msg}"
            logger.error(error_detail)
            raise LLMAuthenticationError(error_detail)

        # Handle other rate limits (429)
        if status_code == 429:
            error_detail = f"Gemini API rate limited: {error_msg}"
            logger.error(error_detail)
            raise LLMRateLimitError(error_detail)

        # Generic API error
        error_detail = f"Gemini API error ({status_code}): {error_text}"
        logger.error(error_detail)
        raise LLMServiceError(error_detail)

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
                    self._parse_gemini_error(response.status_code, response.text)
                    # If we get here, exception was raised above
                    return ""  # Unreachable, but satisfies type checker

                result = response.json()

                # Extract text from Gemini response
                try:
                    simplified_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
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
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError):
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
                    self._parse_gemini_error(response.status_code, response.text)
                    # If we get here, exception was raised above
                    return {}  # Unreachable, but satisfies type checker

                result = response.json()

                try:
                    response_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()

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
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError):
            # Re-raise specific error types without wrapping
            raise
        except Exception as e:
            error_msg = f"Error in Gemini structured simplification: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)


class GroqProvider(LLMProvider):
    """Groq API provider"""

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
                    error_msg = f"Groq API error ({response.status_code}): {response.text}"
                    logger.error(error_msg)
                    # Handle specific error types
                    if response.status_code == 429:
                        # Check if it's a rate limit or quota issue
                        if "rate limit" in response.text.lower():
                            raise LLMRateLimitError(error_msg)
                        else:
                            raise LLMQuotaExhaustedError(error_msg)
                    elif response.status_code in (401, 403):
                        raise LLMAuthenticationError(error_msg)
                    else:
                        raise LLMServiceError(error_msg)

                result = response.json()
                simplified_text = result["choices"][0]["message"]["content"].strip()

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
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError):
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
                    error_msg = f"Groq API error ({response.status_code}): {response.text}"
                    logger.error(error_msg)
                    # Handle specific error types
                    if response.status_code == 429:
                        # Check if it's a rate limit or quota issue
                        if "rate limit" in response.text.lower():
                            raise LLMRateLimitError(error_msg)
                        else:
                            raise LLMQuotaExhaustedError(error_msg)
                    elif response.status_code in (401, 403):
                        raise LLMAuthenticationError(error_msg)
                    else:
                        raise LLMServiceError(error_msg)

                result = response.json()
                response_text = result["choices"][0]["message"]["content"].strip()

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
                    error_msg = f"OpenRouter API error ({response.status_code}): {response.text}"
                    logger.error(error_msg)
                    # Handle specific error types
                    if response.status_code == 429:
                        # Check if it's a rate limit or quota issue
                        if "rate limit" in response.text.lower():
                            raise LLMRateLimitError(error_msg)
                        else:
                            raise LLMQuotaExhaustedError(error_msg)
                    elif response.status_code in (401, 403):
                        raise LLMAuthenticationError(error_msg)
                    else:
                        raise LLMServiceError(error_msg)

                result = response.json()
                simplified_text = result["choices"][0]["message"]["content"].strip()

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
        except (LLMQuotaExhaustedError, LLMAuthenticationError, LLMRateLimitError):
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
                    error_msg = f"OpenRouter API error ({response.status_code}): {response.text}"
                    logger.error(error_msg)
                    # Handle specific error types
                    if response.status_code == 429:
                        # Check if it's a rate limit or quota issue
                        if "rate limit" in response.text.lower():
                            raise LLMRateLimitError(error_msg)
                        else:
                            raise LLMQuotaExhaustedError(error_msg)
                    elif response.status_code in (401, 403):
                        raise LLMAuthenticationError(error_msg)
                    else:
                        raise LLMServiceError(error_msg)

                result = response.json()
                response_text = result["choices"][0]["message"]["content"].strip()

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
    attempts = 0

    while attempts < max_attempts:
        attempts += 1
        try:
            logger.info(f"Simplification attempt {attempts}/{max_attempts}")
            simplified_text = provider.simplify_text(text, target_grade_level)
            return simplified_text, attempts, provider.model
        except LLMServiceError as e:
            logger.warning(f"Simplification attempt {attempts} failed: {str(e)}")
            if attempts >= max_attempts:
                raise
            # Wait before retry (exponential backoff)
            time.sleep(2 ** attempts)

    raise LLMServiceError(f"Simplification failed after {max_attempts} attempts")


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
    start_time = time.time()

    try:
        provider = get_llm_provider()

        # Check text length and chunk if necessary
        chunks = chunk_text_for_simplification(text, settings.CHUNK_SIZE)
        
        # Initialize key_terms and sections to ensure they are always defined
        key_terms = []
        sections = []

        if len(chunks) > 1:
            logger.info(f"Processing {len(chunks)} chunks separately")
            simplified_chunks = []

            # Determine fallback providers (excluding MockProvider and current provider)
            fallback_providers = []
            current_provider_type = type(provider)
            
            # Define provider classes in order of preference for fallback
            provider_classes = [
                ("gemini", lambda: GeminiProvider()),
                ("groq", lambda: GroqProvider()),
                ("openrouter", lambda: OpenRouterProvider()),
                ("openai", lambda: OpenAIProvider())
            ]
            
            # Check which providers are configured and add them to fallback list
            for provider_name, provider_factory in provider_classes:
                try:
                    # Skip if this is the same type as current provider
                    if provider_factory().__class__ == current_provider_type:
                        continue
                    
                    # Try to instantiate the provider to see if it's configured
                    candidate_provider = provider_factory()
                    fallback_providers.append(candidate_provider)
                except LLMServiceError:
                    # Provider not configured (missing API key), skip it
                    continue
                except Exception:
                    # Other instantiation error, skip it
                    continue

            for i, chunk in enumerate(chunks):
                simplified_chunk = None
                last_error = None
                
                # Try current provider first
                try:
                    simplified_chunk = provider.simplify_text(chunk, target_grade_level)
                except (LLMRateLimitError, LLMQuotaExhaustedError) as e:
                    last_error = e
                    logger.warning(f"Chunk {i+1}/{len(chunks)} failed with rate limit/quota error on {type(provider).__name__}: {str(e)}")
                    
                    # Try fallback providers
                    for fallback_provider in fallback_providers:
                        try:
                            logger.info(f"Trying fallback provider {type(fallback_provider).__name__} for chunk {i+1}")
                            simplified_chunk = fallback_provider.simplify_text(chunk, target_grade_level)
                            logger.info(f"Chunk {i+1} succeeded with fallback provider {type(fallback_provider).__name__}")
                            break
                        except (LLMRateLimitError, LLMQuotaExhaustedError) as fallback_error:
                            last_error = fallback_error
                            logger.warning(f"Fallback provider {type(fallback_provider).__name__} also failed with rate limit/quota error: {str(fallback_error)}")
                            continue
                        except LLMServiceError as fallback_error:
                            # Don't try other fallbacks for non-rate-limit errors
                            last_error = fallback_error
                            logger.warning(f"Fallback provider {type(fallback_provider).__name__} failed with non-rate-limit error: {str(fallback_error)}")
                            break
                
                # If all providers failed, raise the last error
                if simplified_chunk is None:
                    logger.error(f"All providers failed for chunk {i+1}")
                    raise last_error
                
                simplified_chunks.append(simplified_chunk)

            simplified_text = "\n\n".join(simplified_chunks)
        else:
            # Try structured simplification first, fall back to regular
            try:
                structured_result = provider.generate_structured_simplification(text, target_grade_level)
                simplified_text = structured_result["simplified_text"]
                key_terms = structured_result.get("key_terms", [])
                sections = structured_result.get("sections", [])
            except LLMServiceError:
                logger.warning("Structured simplification failed, falling back to regular")
                simplified_text = provider.simplify_text(text, target_grade_level)
                # key_terms and sections remain as initialized empty lists

        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "document_id": document_id,
            "original_text": text,
            "simplified_text": simplified_text,
            "target_grade_level": target_grade_level,
            "model_used": provider.model,
            "processing_time_ms": processing_time_ms,
            "sections": sections,
            "key_terms": key_terms,
            "metadata": {
                "chunks": len(chunks),
                "retry_count": 0
            }
        }

    except LLMServiceError as e:
        raise
    except Exception as e:
        error_msg = f"Unexpected error in simplification pipeline: {str(e)}"
        logger.error(error_msg)
        raise LLMServiceError(error_msg)
