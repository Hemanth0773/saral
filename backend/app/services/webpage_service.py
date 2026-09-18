"""
Webpage extraction service.
Handles text extraction from government webpages using BeautifulSoup.
"""

import requests
from bs4 import BeautifulSoup
from typing import Tuple
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_text_from_url(url: str) -> Tuple[str, int]:
    """
    Extract text from a webpage.

    Args:
        url: URL to fetch and extract from

    Returns:
        Tuple of (text, status_code)

    Raises:
        ValueError: If fetch fails, timeout, or invalid HTML
        requests.RequestException: Network errors
    """
    try:
        # Fetch webpage with timeout
        logger.info(f"Fetching URL: {url}")
        response = requests.get(
            url,
            timeout=settings.URL_FETCH_TIMEOUT,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            allow_redirects=True,
            verify=True
        )

        # Check status code
        if response.status_code != 200:
            raise ValueError(f"HTTP {response.status_code} - Failed to fetch URL")

        # Check content size
        content_size = len(response.content)
        if content_size > settings.URL_FETCH_MAX_SIZE:
            raise ValueError(f"Response too large ({content_size} bytes, max {settings.URL_FETCH_MAX_SIZE})")

        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            raise ValueError(f"Invalid content type: {content_type}")

        # Parse HTML
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            raise ValueError(f"Failed to parse HTML: {str(e)}")

        # Extract text
        text = _extract_meaningful_text(soup)

        if not text.strip():
            raise ValueError("No meaningful text could be extracted from webpage")

        logger.info(f"Successfully extracted {len(text)} chars from {url}")
        return text, response.status_code

    except requests.Timeout:
        logger.error(f"Request timeout for URL: {url}")
        raise ValueError(f"Request timeout (max {settings.URL_FETCH_TIMEOUT}s)")
    except requests.ConnectionError as e:
        logger.error(f"Connection error for URL {url}: {str(e)}")
        raise ValueError(f"Failed to connect to URL: {str(e)}")
    except requests.RequestException as e:
        logger.error(f"Request error for URL {url}: {str(e)}")
        raise ValueError(f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error extracting from URL {url}: {str(e)}")
        raise


def _extract_meaningful_text(soup: BeautifulSoup) -> str:
    """
    Extract meaningful text from parsed HTML, removing noise.

    Args:
        soup: BeautifulSoup parsed HTML

    Returns:
        Cleaned text content
    """
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Remove navigation and footer
    for nav in soup(["nav", "footer", "header"]):
        nav.decompose()

    # Remove common noise tags
    for noise in soup(["iframe", "noscript", "meta", "link"]):
        noise.decompose()

    # Get text
    text = soup.get_text()

    # Clean whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)

    return text


def get_webpage_title(url: str) -> str:
    """
    Extract webpage title.

    Args:
        url: URL to fetch

    Returns:
        Page title, or empty string if not found

    Raises:
        ValueError: If fetch fails
    """
    try:
        response = requests.get(
            url,
            timeout=settings.URL_FETCH_TIMEOUT,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
            allow_redirects=True,
            verify=True
        )

        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(response.content, 'html.parser')
        title_tag = soup.find('title')
        return title_tag.string if title_tag else ""

    except Exception as e:
        logger.warning(f"Failed to extract title from {url}: {str(e)}")
        return ""


def get_webpage_metadata(url: str) -> dict:
    """
    Extract metadata from webpage (title, description, language).

    Args:
        url: URL to fetch

    Returns:
        Dictionary with metadata

    Raises:
        ValueError: If fetch fails
    """
    try:
        response = requests.get(
            url,
            timeout=settings.URL_FETCH_TIMEOUT,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
            allow_redirects=True,
            verify=True
        )

        if response.status_code != 200:
            raise ValueError(f"HTTP {response.status_code}")

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract metadata
        metadata = {
            "title": "",
            "description": "",
            "language": "",
            "charset": "",
        }

        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata["title"] = title_tag.string

        # Description (from meta tag)
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag:
            metadata["description"] = desc_tag.get('content', '')

        # Language (from html tag)
        html_tag = soup.find('html')
        if html_tag:
            metadata["language"] = html_tag.get('lang', '')

        # Charset (from meta tag)
        charset_tag = soup.find('meta', attrs={'charset': True})
        if charset_tag:
            metadata["charset"] = charset_tag.get('charset', '')

        return metadata

    except Exception as e:
        logger.warning(f"Failed to extract metadata from {url}: {str(e)}")
        return {
            "title": "",
            "description": "",
            "language": "",
            "charset": "",
        }
