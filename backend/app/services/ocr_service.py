"""
OCR (Optical Character Recognition) service for scanned documents.
Handles image-based PDFs and image files using Tesseract OCR.
"""

import pytesseract
from PIL import Image
import io
from pathlib import Path
from typing import Tuple, List, Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def ocr_image(file_path: str) -> Tuple[str, float]:
    """
    Extract text from an image file using Tesseract OCR.

    Args:
        file_path: Path to image file (JPG, PNG, etc.)

    Returns:
        Tuple of (extracted_text, confidence_score)
        Confidence is 0-1, where 1.0 is perfect confidence

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If OCR fails
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"Image file not found: {file_path}")

    try:
        logger.info(f"Extracting text from image: {file_path}")

        # Open image
        image = Image.open(file_path)

        # Extract text using Tesseract
        text = pytesseract.image_to_string(image, config=f'--psm 6')

        # Estimate confidence (simplified - Tesseract doesn't always provide this)
        # In production, could use pytesseract.image_to_data for confidence scores
        confidence = estimate_ocr_confidence(text)

        if not text.strip():
            logger.warning(f"OCR returned empty text for: {file_path}")
            raise ValueError("OCR could not extract any text from image")

        logger.info(f"Successfully extracted {len(text)} chars from image")
        return text, confidence

    except pytesseract.TesseractNotFoundError as e:
        logger.error(f"Tesseract not installed: {str(e)}")
        raise ValueError("Tesseract OCR is not installed. Please install it from: https://github.com/UB-Mannheim/tesseract/wiki")
    except Exception as e:
        logger.error(f"OCR failed: {str(e)}")
        raise ValueError(f"OCR processing failed: {str(e)}")


def ocr_pdf_images(file_path: str) -> Tuple[str, int]:
    """
    Extract text from image-based PDF by converting pages to images and OCRing.

    Args:
        file_path: Path to PDF file

    Returns:
        Tuple of (combined_text, total_pages_processed)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If processing fails
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    try:
        from pypdf import PdfReader

        logger.info(f"Extracting images from PDF: {file_path}")

        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)

            if page_count == 0:
                raise ValueError("PDF has no pages")

            if page_count > settings.MAX_OCR_PAGES:
                logger.warning(f"PDF has {page_count} pages, limiting to {settings.MAX_OCR_PAGES}")
                page_count = settings.MAX_OCR_PAGES

            text_parts = []
            pages_processed = 0

            # Process each page
            for page_num in range(page_count):
                try:
                    page = pdf_reader.pages[page_num]

                    # Try to get images from page
                    if "/XObject" in page["/Resources"]:
                        xObject = page["/Resources"]["/XObject"].get_object()
                        for obj in xObject:
                            if xObject[obj]["/Subtype"] == "/Image":
                                # Extract image and OCR it
                                image_data = xObject[obj].get_data()
                                image = Image.open(io.BytesIO(image_data))

                                # OCR the image
                                text = pytesseract.image_to_string(image, config='--psm 6')
                                if text.strip():
                                    text_parts.append(f"\n--- Page {page_num + 1} (OCR'd) ---\n{text}")
                                    pages_processed += 1

                except Exception as e:
                    logger.warning(f"Failed to process images on page {page_num + 1}: {str(e)}")
                    text_parts.append(f"\n[Page {page_num + 1} - Image extraction failed]\n")

            combined_text = "".join(text_parts)

            if not combined_text.strip():
                raise ValueError("No text could be extracted from PDF images")

            logger.info(f"Successfully processed {pages_processed} pages from PDF")
            return combined_text, pages_processed

    except Exception as e:
        logger.error(f"PDF image extraction failed: {str(e)}")
        raise ValueError(f"Failed to extract images from PDF: {str(e)}")


def estimate_ocr_confidence(text: str) -> float:
    """
    Estimate confidence of OCR result based on text quality heuristics.

    Args:
        text: Extracted text

    Returns:
        Confidence score 0-1
    """
    if not text or len(text.strip()) == 0:
        return 0.0

    # Count suspicious patterns
    issues = 0
    total_checks = 0

    # Check for excessive special characters (might indicate OCR errors)
    total_checks += 1
    special_char_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text)
    if special_char_ratio > 0.3:  # More than 30% special chars is suspicious
        issues += 1

    # Check for very short text (might not be enough context)
    total_checks += 1
    if len(text.split()) < 10:
        issues += 0.5  # Slight penalty, not a full issue

    # Calculate confidence
    confidence = max(0.0, 1.0 - (issues / total_checks))

    return round(confidence, 2)


def preprocess_image_for_ocr(image_path: str) -> str:
    """
    Preprocess image to improve OCR accuracy.

    Args:
        image_path: Path to image file

    Returns:
        Path to preprocessed image

    Raises:
        ValueError: If preprocessing fails
    """
    try:
        logger.debug(f"Preprocessing image: {image_path}")

        # Open image
        image = Image.open(image_path)

        # Convert to grayscale if needed
        if image.mode != 'L':
            image = image.convert('L')

        # Enhance contrast (simple approach)
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)  # Increase contrast by 50%

        # Enhance brightness
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)  # Increase brightness by 10%

        # Save preprocessed image
        preprocessed_path = str(Path(image_path).stem) + "_preprocessed.png"
        image.save(preprocessed_path)

        logger.debug(f"Preprocessed image saved to: {preprocessed_path}")
        return preprocessed_path

    except Exception as e:
        logger.warning(f"Image preprocessing failed: {str(e)}, using original")
        return image_path
