"""
Utilities for OCR processing and result combination.
Handles image extraction from PDFs and OCR result aggregation.
"""

import io
from pathlib import Path
from typing import List, Tuple, Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_pdf_images(pdf_path: str) -> List[Tuple[str, int]]:
    """
    Extract images from PDF file, returning paths and page numbers.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of (image_path, page_number) tuples
    """
    try:
        from pypdf import PdfReader
        from PIL import Image

        logger.info(f"Extracting images from PDF: {pdf_path}")

        images = []

        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)

            for page_num, page in enumerate(pdf_reader.pages):
                if "/XObject" in page["/Resources"]:
                    xObject = page["/Resources"]["/XObject"].get_object()

                    for obj_name in xObject:
                        obj = xObject[obj_name]

                        if obj["/Subtype"] == "/Image":
                            try:
                                # Extract image data
                                image_data = obj.get_data()
                                image = Image.open(io.BytesIO(image_data))

                                # Save extracted image
                                image_path = f"extracted_page_{page_num + 1}_{obj_name}.png"
                                image.save(image_path)

                                images.append((image_path, page_num + 1))
                                logger.debug(f"Extracted image from page {page_num + 1}")

                            except Exception as e:
                                logger.warning(f"Failed to extract image on page {page_num + 1}: {str(e)}")

        logger.info(f"Extracted {len(images)} images from PDF")
        return images

    except Exception as e:
        logger.error(f"Failed to extract images from PDF: {str(e)}")
        raise ValueError(f"Image extraction failed: {str(e)}")


def combine_ocr_results(results: List[Dict[str, Any]]) -> str:
    """
    Combine multiple OCR results preserving page structure.

    Args:
        results: List of dictionaries with 'page_number', 'text', 'method' keys

    Returns:
        Combined text with page markers
    """
    try:
        logger.debug(f"Combining {len(results)} OCR results")

        # Sort by page number
        results = sorted(results, key=lambda x: x.get('page_number', 0))

        combined_parts = []

        for result in results:
            page_num = result.get('page_number', '?')
            text = result.get('text', '')
            method = result.get('method', 'unknown')

            if text.strip():
                combined_parts.append(f"\n--- Page {page_num} ({method}) ---\n{text}")

        combined_text = "".join(combined_parts)

        logger.info(f"Combined text: {len(combined_text)} characters")
        return combined_text

    except Exception as e:
        logger.error(f"Failed to combine OCR results: {str(e)}")
        raise ValueError(f"Result combination failed: {str(e)}")


def estimate_ocr_confidence_aggregate(confidences: List[float]) -> float:
    """
    Calculate aggregate OCR confidence from multiple pages.

    Args:
        confidences: List of confidence scores (0-1)

    Returns:
        Aggregate confidence score
    """
    if not confidences:
        return 0.0

    # Average confidence, but penalize if any page is very low
    avg_confidence = sum(confidences) / len(confidences)
    min_confidence = min(confidences)

    # If minimum is very low, pull down the average
    if min_confidence < 0.3:
        avg_confidence = avg_confidence * 0.8  # 20% penalty

    return round(avg_confidence, 2)


def detect_extraction_method(
    has_text: bool,
    has_ocr: bool,
    source_type: str = "pdf"
) -> str:
    """
    Determine extraction method based on what was extracted.

    Args:
        has_text: Whether text was extracted
        has_ocr: Whether OCR was applied
        source_type: 'pdf' or 'image'

    Returns:
        Extraction method string
    """
    if source_type == "image":
        return "image_ocr"
    elif source_type == "pdf":
        if has_text and has_ocr:
            return "pdf_mixed"
        elif has_ocr:
            return "pdf_ocr"
        else:
            return "pdf_text"
    else:
        return "unknown"


def cleanup_extracted_files(file_paths: List[str]) -> None:
    """
    Clean up temporary extracted image files.

    Args:
        file_paths: List of file paths to delete
    """
    for file_path in file_paths:
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.debug(f"Deleted temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {file_path}: {str(e)}")


def detect_language_from_ocr(text: str) -> str:
    """
    Detect language from OCR'd text using heuristics.

    Args:
        text: OCR'd text

    Returns:
        Language code
    """
    if not text:
        return "en"

    # Count ASCII vs non-ASCII characters
    ascii_count = sum(1 for c in text if ord(c) < 128)
    total_count = len(text)

    if total_count == 0:
        return "en"

    ascii_ratio = ascii_count / total_count

    # If mostly ASCII, assume English
    if ascii_ratio > 0.8:
        return "en"

    # Check for specific Unicode ranges (simplified)
    kannada_count = sum(1 for c in text if 0xC80 <= ord(c) <= 0xCFF)
    hindi_count = sum(1 for c in text if 0x900 <= ord(c) <= 0x97F)

    if kannada_count > hindi_count:
        return "kn"
    elif hindi_count > 0:
        return "hi"
    else:
        return "en"
