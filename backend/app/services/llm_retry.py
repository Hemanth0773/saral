"""
Rate-limit aware retry helpers for LLM provider calls.

The providers used by Saral (Groq, Gemini, OpenAI, OpenRouter) signal
temporary failures in different ways:

* Groq answers HTTP 429 with a ``Retry-After`` header, an
  ``x-ratelimit-reset-tokens`` header and a message such as
  ``"Please try again in 22.1775s"``.
* Gemini answers HTTP 429 ``RESOURCE_EXHAUSTED`` or HTTP 503 ``UNAVAILABLE``
  when the model is temporarily overloaded.
* The OpenAI compatible providers answer HTTP 429 with a ``Retry-After``
  header.

This module turns those signals into a bounded retry plan. The delays are
derived from the provider hint when one is available and fall back to
exponential backoff with jitter, so parallel requests do not resynchronise
and immediately burn the quota that is still recovering.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping, Optional

# Default retry behaviour. Mirrored by settings.LLM_* in app.core.config.
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 2.0
DEFAULT_MAX_DELAY = 60.0
DEFAULT_JITTER = 0.25

# "23", "59.94s", "1m30s", "500ms", "2 minutes"
_DURATION_PATTERN = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|milliseconds?|s|seconds?|m|minutes?|h|hours?)?",
    re.IGNORECASE,
)

# "try again in 22.1775s", "retry after 30 seconds", "retry in 1.5 seconds"
_RETRY_IN_TEXT_PATTERN = re.compile(
    r"(?:try\s+again\s+in|retry\s+after|retry\s+in)\s*"
    r"(?:after\s+)?(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>ms|milliseconds?|s|seconds?|m|minutes?)?",
    re.IGNORECASE,
)

_UNIT_SECONDS = {
    "ms": 0.001,
    "millisecond": 0.001,
    "milliseconds": 0.001,
    "s": 1.0,
    "second": 1.0,
    "seconds": 1.0,
    "m": 60.0,
    "minute": 60.0,
    "minutes": 60.0,
    "h": 3600.0,
    "hour": 3600.0,
    "hours": 3600.0,
}


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry plan for a single provider call."""

    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    base_delay: float = DEFAULT_BASE_DELAY
    max_delay: float = DEFAULT_MAX_DELAY
    jitter: float = DEFAULT_JITTER

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must not be negative")
        if self.max_delay < 0:
            raise ValueError("max_delay must not be negative")
        if not 0 <= self.jitter <= 1:
            raise ValueError("jitter must be between 0 and 1")


def _normalise_unit(unit: Optional[str]) -> str:
    if not unit:
        return "s"
    return unit.lower().rstrip("s") + "s" if unit.lower().endswith("s") else unit.lower()


def parse_duration(value: Any) -> Optional[float]:
    """
    Parses a duration into seconds.

    Accepts plain seconds ("23"), suffixed values ("59.94s", "500ms",
    "1m30s") and HTTP dates. Returns ``None`` for anything that cannot be
    understood, so callers can fall back to their own backoff.
    """
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    # HTTP date (used by the Retry-After header).
    if "," in text or re.match(r"^\d{2}:\d{2}", text):
        try:
            target = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            target = None
        if target is not None:
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            delta = (target - datetime.now(timezone.utc)).total_seconds()
            return max(0.0, delta)

    total = 0.0
    matched = False
    for match in _DURATION_PATTERN.finditer(text):
        try:
            amount = float(match.group("value"))
        except (TypeError, ValueError):
            continue
        unit = _normalise_unit(match.group("unit"))
        total += amount * _UNIT_SECONDS.get(unit, 1.0)
        matched = True

    if not matched:
        return None

    return max(0.0, total)


def extract_retry_hint(
    headers: Optional[Mapping[str, Any]],
    error_text: Optional[str],
) -> Optional[float]:
    """
    Returns the number of seconds the provider asked us to wait.

    Priority: the ``Retry-After`` header, then the Groq specific
    ``x-ratelimit-reset-tokens`` header, then a duration parsed out of the
    error message. The provider hint always wins over our own backoff so we
    never retry before the provider said it is safe to.
    """
    if headers is not None:
        for name in ("retry-after", "Retry-After"):
            try:
                raw = headers.get(name)
            except Exception:  # pragma: no cover - defensive, MagicMock headers
                raw = None
            delay = parse_duration(raw)
            if delay is not None:
                return delay

        for name in ("x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
            try:
                raw = headers.get(name)
            except Exception:  # pragma: no cover - defensive
                raw = None
            delay = parse_duration(raw)
            if delay is not None:
                return delay

    if isinstance(error_text, str) and error_text:
        match = _RETRY_IN_TEXT_PATTERN.search(error_text)
        if match:
            try:
                amount = float(match.group("value"))
            except (TypeError, ValueError):
                amount = None
            if amount is not None:
                unit = _normalise_unit(match.group("unit"))
                return max(0.0, amount * _UNIT_SECONDS.get(unit, 1.0))

    return None


def compute_retry_delay(
    attempt: int,
    policy: RetryPolicy,
    provider_hint: Optional[float] = None,
    rng: Optional[random.Random] = None,
) -> float:
    """
    Computes how long to wait before the next attempt.

    The delay grows exponentially (``base_delay * 2 ** (attempt - 1)``) and is
    jittered by +/- ``policy.jitter`` so concurrent clients do not retry in
    lockstep. A provider supplied hint is treated as a lower bound: we never
    retry earlier than the provider asked, but we may wait longer.
    """
    attempt = max(1, attempt)
    exponential = policy.base_delay * (2 ** (attempt - 1))
    generator = rng or random

    delay = exponential * (1 + generator.uniform(-policy.jitter, policy.jitter))

    if provider_hint is not None and provider_hint > 0:
        delay = max(delay, provider_hint)

    return max(0.0, min(delay, policy.max_delay))


def is_retryable_exception(error: BaseException) -> bool:
    """
    Decides whether an error is worth retrying.

    Authentication failures are permanent and are never retried. Rate limits,
    exhausted quotas, transient service errors and generic provider errors are
    retried, but always within a bounded attempt budget.
    """
    # Imported lazily to avoid a circular import with app.services.llm_service.
    from app.services.llm_service import (
        LLMAuthenticationError,
        LLMServiceError,
    )

    if isinstance(error, LLMAuthenticationError):
        return False
    if isinstance(error, LLMServiceError):
        return True
    return False
