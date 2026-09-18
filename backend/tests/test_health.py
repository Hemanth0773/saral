"""
Unit tests for health check endpoint
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health_check():
    """Test that health endpoint returns ok status"""
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Cognitive Accessibility Simplifier"
    assert data["version"] == "1.0.0"
    assert data["environment"] == "development"
    assert "timestamp" in data


def test_root_endpoint():
    """Test root endpoint redirects to docs"""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert "docs" in data
    assert data["docs"] == "/docs"
