"""
File utilities for document processing.
Handles file saving, cleanup, and management.
"""

import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.core.logging import get_logger
from app.core.security import sanitize_filename

logger = get_logger(__name__)


def save_uploaded_file(file_content: bytes, original_filename: str, upload_dir: str) -> str:
    """
    Save uploaded file to disk with safe filename.

    Args:
        file_content: Binary file content
        original_filename: Original filename from upload
        upload_dir: Directory to save file to

    Returns:
        Full path to saved file

    Raises:
        IOError: If file cannot be saved
    """
    try:
        # Create upload directory if it doesn't exist
        Path(upload_dir).mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_filename = sanitize_filename(original_filename)

        # Add timestamp and random hash to ensure uniqueness
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        random_hash = uuid.uuid4().hex[:8]
        name_without_ext = safe_filename.rsplit(".", 1)[0]
        ext = safe_filename.rsplit(".", 1)[1] if "." in safe_filename else "bin"
        unique_filename = f"{name_without_ext}_{timestamp}_{random_hash}.{ext}"

        # Full path
        file_path = os.path.join(upload_dir, unique_filename)

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File saved: {file_path} (size: {len(file_content)} bytes)")
        return file_path

    except Exception as e:
        logger.error(f"Failed to save file {original_filename}: {str(e)}")
        raise IOError(f"Failed to save file: {str(e)}")


def clean_temp_file(file_path: str) -> bool:
    """
    Delete temporary file safely.

    Args:
        file_path: Path to file to delete

    Returns:
        True if deleted, False if file doesn't exist or error occurred
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Deleted temp file: {file_path}")
            return True
        else:
            logger.debug(f"File not found for cleanup: {file_path}")
            return False
    except Exception as e:
        logger.warning(f"Failed to delete temp file {file_path}: {str(e)}")
        return False


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.

    Args:
        file_path: Path to file

    Returns:
        File size in bytes, or 0 if file doesn't exist
    """
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def ensure_upload_directory(upload_dir: str) -> bool:
    """
    Ensure upload directory exists and is writable.

    Args:
        upload_dir: Path to upload directory

    Returns:
        True if directory is ready, False otherwise
    """
    try:
        Path(upload_dir).mkdir(parents=True, exist_ok=True)
        # Test write permission
        test_file = os.path.join(upload_dir, ".test_write")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        logger.debug(f"Upload directory verified: {upload_dir}")
        return True
    except Exception as e:
        logger.error(f"Upload directory not ready: {upload_dir} - {str(e)}")
        return False
