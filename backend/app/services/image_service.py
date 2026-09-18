"""
Image processing service for OCR preparation and validation.
Handles image format validation, preprocessing, and extraction.
"""

from PIL import Image
import io
from pathlib import Path
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_image_format(file_path: str) -> bool:
    """
    Validate that file is a proper image format.

    Args:
        file_path: Path to image file

    Returns:
        True if valid, False otherwise
    """
    try:
        image = Image.open(file_path)
        # Verify the image can be loaded
        image.verify()
        logger.debug(f"Image format validated: {file_path}")
        return True
    except Exception as e:
        logger.warning(f"Image validation failed: {str(e)}")
        return False


def extract_text_from_image(file_path: str) -> str:
    """
    Extract text from image file using OCR.

    Args:
        file_path: Path to image file

    Returns:
        Extracted text

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If extraction fails
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"Image file not found: {file_path}")

    try:
        # Import here to avoid circular dependency
        from app.services.ocr_service import ocr_image

        text, confidence = ocr_image(file_path)
        logger.info(f"Extracted text from image (confidence: {confidence})")
        return text

    except Exception as e:
        logger.error(f"Failed to extract text from image: {str(e)}")
        raise ValueError(f"Image text extraction failed: {str(e)}")


def detect_image_rotation(file_path: str) -> Optional[int]:
    """
    Detect if image needs rotation based on EXIF data.

    Args:
        file_path: Path to image file

    Returns:
        Rotation angle (0, 90, 180, 270) or None if no rotation
    """
    try:
        image = Image.open(file_path)

        # Check EXIF data for orientation
        try:
            from PIL.ExifTags import TAGS
            exif_data = image._getexif()

            if exif_data:
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    if tag_name == "Orientation":
                        # EXIF orientation codes
                        orientation_map = {
                            1: 0,
                            3: 180,
                            6: 270,
                            8: 90,
                        }
                        rotation = orientation_map.get(value, 0)
                        if rotation != 0:
                            logger.info(f"Detected image rotation: {rotation} degrees")
                        return rotation if rotation != 0 else None
        except (AttributeError, KeyError, IndexError):
            # No EXIF data available
            pass

        return None

    except Exception as e:
        logger.warning(f"Could not detect image rotation: {str(e)}")
        return None


def correct_image_rotation(file_path: str) -> str:
    """
    Correct image rotation based on EXIF data.

    Args:
        file_path: Path to image file

    Returns:
        Path to rotated image (same path if no rotation needed)
    """
    try:
        image = Image.open(file_path)
        rotation = detect_image_rotation(file_path)

        if rotation:
            # Rotate image
            rotated_image = image.rotate(-rotation, expand=True)
            # Save back
            rotated_image.save(file_path)
            logger.info(f"Image rotated by {rotation} degrees")

        return file_path

    except Exception as e:
        logger.warning(f"Image rotation correction failed: {str(e)}")
        return file_path


def enhance_image_for_ocr(file_path: str) -> str:
    """
    Enhance image for better OCR accuracy.

    Args:
        file_path: Path to image file

    Returns:
        Path to enhanced image

    Raises:
        ValueError: If enhancement fails
    """
    try:
        logger.debug(f"Enhancing image for OCR: {file_path}")

        image = Image.open(file_path)

        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')

        # Enhance contrast
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)  # Double the contrast

        # Enhance sharpness
        from PIL import ImageFilter
        image = image.filter(ImageFilter.SHARPEN)

        # Save enhanced image
        enhanced_path = str(Path(file_path).stem) + "_enhanced.png"
        image.save(enhanced_path)

        logger.debug(f"Enhanced image saved to: {enhanced_path}")
        return enhanced_path

    except Exception as e:
        logger.warning(f"Image enhancement failed: {str(e)}, using original")
        return file_path


def get_image_metadata(file_path: str) -> dict:
    """
    Extract image metadata.

    Args:
        file_path: Path to image file

    Returns:
        Dictionary with image metadata
    """
    try:
        image = Image.open(file_path)

        metadata = {
            "format": image.format,
            "size": image.size,
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "has_alpha": image.mode in ('RGBA', 'LA', 'PA'),
        }

        logger.debug(f"Image metadata: {metadata}")
        return metadata

    except Exception as e:
        logger.warning(f"Could not extract image metadata: {str(e)}")
        return {}
