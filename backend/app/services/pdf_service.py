"""
PDF document extraction service.
Handles text extraction from PDF files using pypdf (pure Python, no C++ required).
"""

from pypdf import PdfReader
from pathlib import Path
from typing import Tuple, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(file_path: str) -> Tuple[str, str, int]:
    """
    Extract text from a PDF file.

    Args:
        file_path: Path to PDF file

    Returns:
        Tuple of (text, extraction_method, page_count)
        extraction_method: "pdf_text" or "pdf_image_stub"

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If PDF is corrupted or cannot be read
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    try:
        # Open and read PDF
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)

            if page_count == 0:
                raise ValueError("PDF has no pages")

            # Track extraction method
            extraction_method = "pdf_text"
            text_parts = []
            image_only_pages = 0

            # Extract text from each page
            for page_num in range(page_count):
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()

                    # If page has very little text, it might be image-based
                    if len(text.strip()) < 10:
                        image_only_pages += 1
                        # Add page marker for readability
                        text_parts.append(f"\n[Page {page_num + 1} - Image content]\n")
                    else:
                        text_parts.append(f"\n--- Page {page_num + 1} ---\n")
                        text_parts.append(text)

                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {str(e)}")
                    text_parts.append(f"\n[Page {page_num + 1} - Extraction failed]\n")

            # If most pages are image-based, mark as such (OCR in future milestone)
            if image_only_pages > page_count * 0.5:
                extraction_method = "pdf_image_stub"
                logger.info(f"PDF appears to be image-based ({image_only_pages}/{page_count} pages)")

            combined_text = "".join(text_parts)

            if not combined_text.strip():
                raise ValueError("No text could be extracted from PDF")

            logger.info(f"Successfully extracted text from PDF: {page_count} pages, {len(combined_text)} chars, method={extraction_method}")
            return combined_text, extraction_method, page_count

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

