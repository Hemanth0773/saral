"""
PDF document extraction service.
Handles text extraction from PDF files using pypdf and OCR context.
"""

from pypdf import PdfReader
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(file_path: str) -> Tuple[str, str, int]:
    """
    Extract text from a PDF file.

    Args:
        file_path: Path to PDF file

    Returns:
        Tuple of (text, extraction_method, page_count)
        extraction_method: "pdf_text", "pdf_ocr", or "pdf_mixed"

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If PDF is corrupted or cannot be read
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    try:
        # Import OCR utilities locally to avoid circular dependencies
        from app.utils.ocr_utils import extract_pdf_images, cleanup_extracted_files
        from app.services.ocr_service import ocr_pdf_images

        # Open and read PDF
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)

            if page_count == 0:
                raise ValueError("PDF has no pages")

            # Track extraction method
            has_text = False
            has_images = False
            text_parts = []

            # Step 1: First try standard text extraction
            text_pages = 0
            image_only_pages = 0

            for page_num in range(page_count):
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()

                    if text and len(text.strip()) > 50:
                        # Page has good text
                        has_text = True
                        text_pages += 1
                        text_parts.append({
                            "page_number": page_num + 1,
                            "text": text,
                            "method": "text"
                        })
                    else:
                        # Page is mostly images or empty
                        image_only_pages += 1
                        has_images = True

                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {str(e)}")
                    image_only_pages += 1
                    has_images = True

            # Combine the results into a final text based on what we found
            final_text = ""
            extraction_method = "pdf_text"

            # Case 1: Pure text PDF
            if has_text and image_only_pages == 0:
                extraction_method = "pdf_text"
                from app.utils.ocr_utils import combine_ocr_results
                final_text = combine_ocr_results(text_parts)

            # Case 2: Pure image PDF or Mixed PDF (Needs OCR)
            elif has_images:
                try:
                    # Let the OCR service handle extracting and processing images
                    logger.info(f"PDF needs OCR ({image_only_pages} image pages discovered)")
                    ocr_text, ocr_pages = ocr_pdf_images(file_path)

                    if has_text and text_pages > 0:
                        # Mixed PDF: Combine text with OCR results
                        extraction_method = "pdf_mixed"
                        # Simple combination for now, preserving page order would be better
                        from app.utils.ocr_utils import combine_ocr_results
                        base_text = combine_ocr_results(text_parts)
                        final_text = base_text + "\n\n--- SCANNED PAGES (OCR) ---\n" + ocr_text
                    else:
                        # Pure Image PDF
                        extraction_method = "pdf_ocr"
                        final_text = ocr_text

                except ValueError as ve:
                    # If Tesseract is not installed, fallback to stub
                    logger.warning(f"OCR not available or failed: {str(ve)}")
                    if has_text:
                        extraction_method = "pdf_text"
                        from app.utils.ocr_utils import combine_ocr_results
                        final_text = combine_ocr_results(text_parts) + "\n\n[Some scanned pages could not be read. Please install Tesseract OCR.]\n"
                    else:
                        extraction_method = "pdf_image_stub"
                        from app.utils.ocr_utils import combine_ocr_results
                        final_text = combine_ocr_results([
                            {"page_number": i+1, "text": "[Image content - No OCR available]", "method": "stub"}
                            for i in range(page_count)
                        ])

            if not final_text.strip():
                raise ValueError("No text could be extracted from PDF")

            logger.info(f"Successfully extracted text from PDF: {page_count} pages, {len(final_text)} chars, method={extraction_method}")
            return final_text, extraction_method, page_count

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error extracting PDF: {str(e)}")
        raise ValueError(f"Failed to extract PDF: {str(e)}")


def get_pdf_metadata(file_path: str) -> dict:
    """
    Extract metadata from PDF file.

    Args:
        file_path: Path to PDF file

    Returns:
        Dictionary with metadata

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If PDF is corrupted
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    try:
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)

            metadata = {
                "page_count": len(pdf_reader.pages),
                "title": pdf_reader.metadata.title if pdf_reader.metadata else "",
                "author": pdf_reader.metadata.author if pdf_reader.metadata else "",
                "subject": pdf_reader.metadata.subject if pdf_reader.metadata else "",
                "creator": pdf_reader.metadata.creator if pdf_reader.metadata else "",
                "producer": pdf_reader.metadata.producer if pdf_reader.metadata else "",
            }

            return metadata

    except Exception as e:
        raise ValueError(f"Failed to read PDF metadata: {str(e)}")


def is_pdf_image_based(file_path: str) -> bool:
    """
    Check if PDF is primarily image-based (needs OCR).

    Args:
        file_path: Path to PDF file

    Returns:
        True if PDF is image-based, False if text-based

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If PDF is corrupted
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    try:
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)

            if page_count == 0:
                return False

            # Check first few pages
            pages_to_check = min(3, page_count)
            text_pages = 0

            for page_num in range(pages_to_check):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if len(text.strip()) > 10:
                    text_pages += 1

            # If less than half have text, it's image-based
            return text_pages < pages_to_check / 2

    except Exception as e:
        logger.warning(f"Could not determine if PDF is image-based: {str(e)}")
        return False

