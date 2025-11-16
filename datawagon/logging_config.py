import logging
import sys
from typing import Optional


def setup_logging(
    level: str = "INFO", format_string: Optional[str] = None
) -> logging.Logger:
    """Configure and return a logger for the datawagon application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for log messages

    Returns:
        Configured logger instance
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Return application-specific logger
    logger = logging.getLogger("datawagon")
    logger.setLevel(getattr(logging, level.upper()))
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name under the datawagon namespace.

    Args:
        name: Name for the logger (typically module name)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"datawagon.{name}")
