"""
Security utilities and middleware for the application.
"""

import logging
import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _is_private_or_blocked_host(hostname: str) -> bool:
    """
    Check if a hostname resolves to or is a private/loopback/link-local IP.

    Uses ipaddress module to detect RFC 1918 private ranges, loopback,
    link-local (e.g. AWS metadata 169.254.169.254), and other non-public IPs.
    """
    # Exact hostname blocklist (covers DNS-level SSRF)
    blocked_hostnames = ("localhost", "0.0.0.0", "::1")
    if hostname.lower() in blocked_hostnames:
        return True

    # If the hostname is a literal IP, validate with ipaddress
    try:
        ip = ipaddress.ip_address(hostname)
        return not ip.is_global or ip.is_loopback or ip.is_link_local
    except ValueError:
        pass

    # Hostname is a domain — resolve it and check each resolved IP
    try:
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            ip_str = info[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
                if not ip.is_global or ip.is_loopback or ip.is_link_local:
                    return True
            except ValueError:
                continue
    except (socket.gaierror, socket.herror, OSError):
        # If resolution fails, treat as safe (let the actual request fail)
        pass

    return False


def validate_file_upload(
    filename: Optional[str],
    file_size_bytes: int,
    max_file_size_mb: int,
    allowed_extensions: tuple = ("pdf", "txt", "docx", "doc", "jpg", "jpeg", "png")
) -> tuple[bool, Optional[str]]:
    """
    Validate uploaded file for security and compliance.

    Args:
        filename: Original filename
        file_size_bytes: File size in bytes
        max_file_size_mb: Maximum allowed size in MB
        allowed_extensions: Tuple of allowed file extensions (lowercase)

    Returns:
        Tuple of (is_valid, error_message)
    """

    # Check filename exists
    if not filename:
        return False, "Filename is required"

    # Check filename length
    if len(filename) > 255:
        return False, "Filename is too long (max 255 characters)"

    # Extract extension
    try:
        extension = filename.rsplit(".", 1)[1].lower()
    except IndexError:
        return False, "File must have an extension"

    # Check allowed extensions
    if extension not in allowed_extensions:
        return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"

    # Check file size
    max_bytes = max_file_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        return False, f"File is too large. Maximum size is {max_file_size_mb} MB"

    if file_size_bytes == 0:
        return False, "File is empty"

    return True, None


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate URL for security (prevent SSRF attacks).

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """

    if not url:
        return False, "URL is required"

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        return False, "Only HTTP and HTTPS URLs are allowed"

    # Check for localhost/private IPs / link-local / blocked hostnames (SSRF protection)
    hostname = parsed.hostname or ""
    if _is_private_or_blocked_host(hostname):
        return False, "Local/private URLs are not allowed"

    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other attacks.

    Args:
        filename: Original filename

    Returns:
        Safe filename
    """
    import os

    # Remove path components
    filename = os.path.basename(filename)

    # Remove dangerous characters
    dangerous_chars = ['/', '\\', '..', '~', '$', '`', '!', '*', '?', '"', "'", '<', '>', '|']
    for char in dangerous_chars:
        filename = filename.replace(char, "_")

    return filename


def create_safe_directory_structure(base_path: str) -> bool:
    """
    Create necessary directories for file uploads and generated content.

    Args:
        base_path: Base directory path

    Returns:
        True if successful, False otherwise
    """
    import os

    try:
        os.makedirs(base_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {base_path}: {str(e)}")
        return False
