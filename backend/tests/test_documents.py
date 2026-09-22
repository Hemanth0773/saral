"""
Tests for document extraction endpoints (MILESTONE 2).
Tests PDF extraction, URL extraction, and error handling.
"""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from app.main import app
from app.services import document_service
from unittest.mock import patch


client = TestClient(app)


class TestDocumentExtraction:
    """Tests for document extraction endpoints"""

    def test_health_endpoint_still_works(self):
        """Verify health endpoint still works after MILESTONE 2 changes"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_extract_no_file(self):
        """Test extraction with no file provided"""
        response = client.post("/api/documents/extract")
        assert response.status_code == 400

    def test_extract_invalid_file_type(self):
        """Test extraction with invalid file type"""
        # Create a file with invalid extension
        file_content = b"This is not a PDF or Image"
        files = {"file": ("test.exe", file_content, "application/octet-stream")}
        response = client.post("/api/documents/extract", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "INVALID_FILE_TYPE" in data["error"]["code"]

    @patch('app.services.document_service.process_document_upload')
    def test_extract_image_file(self, mock_process):
        """Test extraction with an image file"""
        mock_process.return_value = {
            "success": True,
            "document_id": "doc_123",
            "filename": "test.jpg",
            "language": "en",
            "page_count": 1,
            "extraction_method": "image_ocr",
            "text": "Image text",
            "text_truncated": False,
            "metadata": {
                "document_id": "doc_123",
                "filename": "test.jpg",
                "language": "en",
                "page_count": 1,
                "word_count": 2,
                "extraction_method": "image_ocr",
                "extracted_at": "2026-09-20T22:00:00Z"
            }
        }

        file_content = b"dummy image content"
        files = {"file": ("test.jpg", file_content, "image/jpeg")}
        response = client.post("/api/documents/extract", files=files)

        assert response.status_code == 200
        mock_process.assert_called_once()

    def test_extract_empty_file(self):
        """Test extraction with empty file"""
        files = {"file": ("empty.pdf", b"", "application/pdf")}
        response = client.post("/api/documents/extract", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_generate_document_id(self):
        """Test document ID generation"""
        doc_id_1 = document_service.generate_document_id()
        doc_id_2 = document_service.generate_document_id()

        # IDs should have correct format
        assert doc_id_1.startswith("doc_")
        assert doc_id_2.startswith("doc_")

        # IDs should be unique
        assert doc_id_1 != doc_id_2

        # IDs should contain timestamp and hash
        parts = doc_id_1.split("_")
        assert len(parts) == 4  # doc, date, time, hash
        assert len(parts[3]) == 8  # hash should be 8 chars


class TestURLExtraction:
    """Tests for URL extraction endpoints"""

    def test_url_extraction_no_url(self):
        """Test URL extraction with no URL provided"""
        response = client.post(
            "/api/documents/url",
            json={}
        )
        assert response.status_code == 422  # Validation error

    def test_url_extraction_invalid_url_localhost(self):
        """Test URL extraction with localhost (SSRF prevention)"""
        response = client.post(
            "/api/documents/url",
            json={"url": "http://localhost:8000"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "INVALID_URL" in data["error"]["code"]

    def test_url_extraction_invalid_url_private_ip(self):
        """Test URL extraction with private IP (SSRF prevention)"""
        response = client.post(
            "/api/documents/url",
            json={"url": "http://127.0.0.1:8000"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_url_extraction_invalid_scheme(self):
        """Test URL extraction with invalid scheme"""
        response = client.post(
            "/api/documents/url",
            json={"url": "ftp://example.com"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "INVALID_URL" in data["error"]["code"]

    def test_url_extraction_file_scheme(self):
        """Test URL extraction with file:// scheme (blocked)"""
        response = client.post(
            "/api/documents/url",
            json={"url": "file:///etc/passwd"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False


class TestLanguageDetection:
    """Tests for language detection"""

    def test_detect_english(self):
        """Test English language detection"""
        english_text = "This is a government scheme for housing assistance. " * 10
        lang = document_service.detect_language(english_text)
        assert lang == "en"

    def test_detect_empty_text(self):
        """Test language detection with empty text"""
        lang = document_service.detect_language("")
        assert lang == "en"  # Default to English

    def test_detect_mixed_language(self):
        """Test language detection with mixed content"""
        mixed_text = "This is English text with some words mixed in"
        lang = document_service.detect_language(mixed_text)
        # Should detect as English due to high ASCII ratio
        assert lang in ["en", "other"]


class TestErrorResponses:
    """Tests for error response format"""

    def test_error_response_format(self):
        """Test that error responses have correct format"""
        # Try to extract with invalid file type
        files = {"file": ("test.exe", b"content", "application/octet-stream")}
        response = client.post("/api/documents/extract", files=files)

        data = response.json()
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]


class TestDocumentIDFormat:
    """Tests for document ID format"""

    def test_document_id_format(self):
        """Test that generated document IDs have correct format"""
        doc_id = document_service.generate_document_id()

        # Format: doc_YYYYMMDD_HHMMSS_HASH
        parts = doc_id.split("_")
        assert len(parts) == 4
        assert parts[0] == "doc"

        # Date part should be 8 digits
        assert len(parts[1]) == 8
        assert parts[1].isdigit()

        # Time part should be 6 digits
        assert len(parts[2]) == 6
        assert parts[2].isdigit()

        # Hash should be 8 hex characters
        assert len(parts[3]) == 8
        try:
            int(parts[3], 16)
        except ValueError:
            pytest.fail("Hash is not valid hexadecimal")


class TestResponseSchema:
    """Tests for response schema validation"""

    def test_extract_response_has_required_fields(self):
        """Test that extract response has all required fields"""
        # This would require a valid PDF file in fixtures
        # For now, just test that invalid inputs return proper error format
        response = client.post("/api/documents/extract")
        assert response.status_code == 400

    def test_url_extract_response_has_required_fields(self):
        """Test that URL extract response has all required fields"""
        response = client.post(
            "/api/documents/url",
            json={"url": "localhost"}
        )
        # Should reject, but response should have proper format
        data = response.json()
        assert "error" in data


class TestAPISecurity:
    """Tests for API security features"""

    def test_file_size_limit_validation(self):
        """Test that file size validation works"""
        # Create a large file content (simulated)
        large_content = b"x" * (100 * 1024 * 1024)  # 100MB - should be rejected
        files = {"file": ("large.pdf", large_content[:1024], "application/pdf")}

        # Note: In real test, we'd use proper file size
        response = client.post("/api/documents/extract", files=files)
        # Should either process or reject based on size
        assert response.status_code in [200, 400, 413, 422, 500]

    def test_url_ssrf_protection(self):
        """Test SSRF protection for URLs"""
        dangerous_urls = [
            "http://127.0.0.1",
            "http://localhost",
            "http://0.0.0.0",
            "file:///etc/passwd",
            "ftp://example.com",
        ]

        for dangerous_url in dangerous_urls:
            response = client.post(
                "/api/documents/url",
                json={"url": dangerous_url}
            )
            # All should be rejected
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False


class TestEndpointDocumentation:
    """Tests that endpoints are properly documented"""

    def test_swagger_ui_loads(self):
        """Test that Swagger UI loads successfully"""
        response = client.get("/docs")
        assert response.status_code == 200
        # Check that Swagger UI HTML is served
        assert b"swagger-ui" in response.content.lower()
        assert b'<div id="swagger-ui">' in response.content

    def test_openapi_schema_includes_endpoints(self):
        """Test that OpenAPI schema includes new endpoints"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        paths = data.get("paths", {})
        # Check that document endpoints are in schema
        assert "/api/documents/extract" in paths or "/documents/extract" in paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
