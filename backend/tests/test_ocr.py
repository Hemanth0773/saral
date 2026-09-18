"""
Unit tests for OCR service and Image processing (MILESTONE 3).
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from app.services import ocr_service, image_service
from app.utils import ocr_utils


class TestOCRService:
    """Tests for OCR service functionality"""

    @patch('app.services.ocr_service.pytesseract.image_to_string')
    @patch('app.services.ocr_service.Image.open')
    @patch('pathlib.Path.exists')
    def test_ocr_image_success(self, mock_exists, mock_open, mock_tesseract):
        """Test successful OCR on an image"""
        # Setup mocks
        mock_exists.return_value = True
        mock_tesseract.return_value = "This is extracted text from OCR."

        # Execute
        text, confidence = ocr_service.ocr_image("dummy_path.jpg")

        # Verify
        assert text == "This is extracted text from OCR."
        assert confidence >= 0.7  # Should be relatively high for clean text
        mock_exists.assert_called_once()
        mock_open.assert_called_once()
        mock_tesseract.assert_called_once()

    @patch('pathlib.Path.exists')
    def test_ocr_image_file_not_found(self, mock_exists):
        """Test OCR with non-existent file"""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError):
            ocr_service.ocr_image("nonexistent.jpg")

    @patch('app.services.ocr_service.pytesseract.image_to_string')
    @patch('app.services.ocr_service.Image.open')
    @patch('pathlib.Path.exists')
    def test_ocr_image_empty_result(self, mock_exists, mock_open, mock_tesseract):
        """Test OCR handling of empty results (e.g., blank image)"""
        mock_exists.return_value = True
        mock_tesseract.return_value = "   \n  "  # Just whitespace

        with pytest.raises(ValueError, match="could not extract any text"):
            ocr_service.ocr_image("blank_image.jpg")

    def test_estimate_ocr_confidence(self):
        """Test confidence estimation heuristic"""
        # High confidence text
        clean_text = "This is a clean and normal sentence that looks like standard English writing."
        conf = ocr_service.estimate_ocr_confidence(clean_text)
        assert conf > 0.8

        # Low confidence text (lots of special chars)
        messy_text = "Th!s |s @ m3$$y $entence w!th #l0t$ 0f %^&* ch@r$"
        messy_conf = ocr_service.estimate_ocr_confidence(messy_text)
        assert messy_conf < conf

        # Empty text
        empty_conf = ocr_service.estimate_ocr_confidence("")
        assert empty_conf == 0.0


class TestImageService:
    """Tests for Image processing service"""

    @patch('app.services.image_service.Image.open')
    def test_validate_image_format_valid(self, mock_open):
        """Test validation of valid image"""
        mock_img = MagicMock()
        mock_open.return_value = mock_img

        result = image_service.validate_image_format("valid.jpg")

        assert result is True
        mock_img.verify.assert_called_once()

    @patch('app.services.image_service.Image.open')
    def test_validate_image_format_invalid(self, mock_open):
        """Test validation of invalid image"""
        mock_open.side_effect = Exception("Not a valid image file")

        result = image_service.validate_image_format("invalid.jpg")

        assert result is False

    @patch('app.services.image_service.Image.open')
    def test_detect_image_rotation(self, mock_open):
        """Test EXIF rotation detection"""
        # Mock EXIF data indicating 180 degree rotation (orientation=3)
        mock_img = MagicMock()
        mock_img._getexif.return_value = {274: 3}  # 274 is EXIF Orientation tag
        mock_open.return_value = mock_img

        # Patch ExifTags to map 274 to "Orientation"
        with patch('PIL.ExifTags.TAGS', {274: "Orientation"}):
            rotation = image_service.detect_image_rotation("rotated.jpg")

            assert rotation == 180


class TestOCRUtils:
    """Tests for OCR utilities"""

    def test_detect_extraction_method(self):
        """Test prediction of extraction method based on source and results"""
        # Standalone images
        assert ocr_utils.detect_extraction_method(True, True, "image") == "image_ocr"

        # Pure text PDF
        assert ocr_utils.detect_extraction_method(True, False, "pdf") == "pdf_text"

        # Pure image/scanned PDF
        assert ocr_utils.detect_extraction_method(False, True, "pdf") == "pdf_ocr"

        # Mixed PDF
        assert ocr_utils.detect_extraction_method(True, True, "pdf") == "pdf_mixed"

    def test_combine_ocr_results(self):
        """Test combining OCR results with page markers"""
        results = [
            {"page_number": 2, "text": "Page two text", "method": "text"},
            {"page_number": 1, "text": "Page one text", "method": "ocr"},
        ]

        combined = ocr_utils.combine_ocr_results(results)

        # Should be sorted by page number
        assert "Page 1" in combined
        assert "Page 2" in combined
        assert combined.find("Page 1") < combined.find("Page 2")
        assert "Page one text" in combined
        assert "Page two text" in combined

    def test_detect_language_from_ocr(self):
        """Test OCR-specific language detection fallback"""
        # Mostly English/ASCII
        en_text = "This is standard English."
        assert ocr_utils.detect_language_from_ocr(en_text) == "en"

        # Just to test it doesn't crash on empty
        assert ocr_utils.detect_language_from_ocr("") == "en"


# Let's fix test_documents.py so we don't break existing tests with the service signature change
# We changed process_pdf_upload to process_document_upload
