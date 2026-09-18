"""
Structured logging configuration for the application.
"""

import logging
import sys
from app.core.config import settings


def setup_logging():
    """
    Configure structured logging for the application.
    Logs to console with a standard format.
    """

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(settings.LOG_LEVEL)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)

    # Formatter with timestamp, level, logger name, and message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # Suppress verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    Use this in all modules.

    Example:
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return logging.getLogger(name)
