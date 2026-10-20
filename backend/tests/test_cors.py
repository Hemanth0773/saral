"""
Tests for the CORS configuration used by the Saral browser extension.

The extension calls the backend from a "chrome-extension://<id>" origin, which
cannot be listed statically. The backend therefore matches extension origins
with a pattern while keeping the explicit web origin allow-list intact.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


client = TestClient(app)

EXTENSION_ORIGIN = "chrome-extension://abcdefghijklmnopqrstuvwxyz012345"
ALLOWED_WEB_ORIGIN = "http://localhost:3000"
BLOCKED_WEB_ORIGIN = "https://not-allowed.example.com"


def test_extension_origin_is_allowed():
    """A Chrome extension origin is echoed back in the CORS header."""
    response = client.get("/api/health", headers={"Origin": EXTENSION_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == EXTENSION_ORIGIN


def test_configured_web_origin_is_still_allowed():
    """The existing website origins keep working."""
    response = client.get("/api/health", headers={"Origin": ALLOWED_WEB_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_WEB_ORIGIN


def test_unknown_web_origin_is_not_allowed():
    """An arbitrary web origin is still rejected - CORS is not widened."""
    response = client.get("/api/health", headers={"Origin": BLOCKED_WEB_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None


def test_similar_but_invalid_extension_origins_are_rejected():
    """Only real Chrome extension ids (32 chars) are matched."""
    for origin in (
        "chrome-extension://short",
        "chrome-extension://",
        "https://abcdefghijklmnopqrstuvwxyz012345",
    ):
        response = client.get("/api/health", headers={"Origin": origin})
        assert response.headers.get("access-control-allow-origin") is None, origin


def test_preflight_request_from_the_extension_is_allowed():
    """A CORS preflight from the extension succeeds for the API routes."""
    response = client.options(
        "/api/documents/simplify",
        headers={
            "Origin": EXTENSION_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == EXTENSION_ORIGIN
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_cors_origin_regex_is_configurable():
    """The pattern is exposed through settings so it can be tightened or removed."""
    assert settings.CORS_ORIGIN_REGEX
    assert "chrome-extension" in settings.CORS_ORIGIN_REGEX


@pytest.mark.parametrize("origin", ["http://127.0.0.1:3000", "http://127.0.0.1:8000"])
def test_local_frontend_origins_are_allowed(origin):
    """Every origin on the configured allow-list is echoed back."""
    if origin not in settings.CORS_ORIGINS:
        pytest.skip(f"{origin} is not on the configured allow-list")

    response = client.get("/api/health", headers={"Origin": origin})
    assert response.headers.get("access-control-allow-origin") == origin


def test_every_configured_web_origin_is_allowed():
    """The configured allow-list is honoured exactly as declared."""
    for origin in settings.CORS_ORIGINS:
        response = client.get("/api/health", headers={"Origin": origin})
        assert response.headers.get("access-control-allow-origin") == origin, origin
