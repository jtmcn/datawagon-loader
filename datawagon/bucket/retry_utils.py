"""Retry decorator with exponential backoff for transient failures."""
import functools
import time
from typing import Callable, Tuple, Type

from datawagon.logging_config import get_logger

logger = get_logger(__name__)


def retry_with_backoff(
    retries: int = 3,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator to retry a function with exponential backoff.

    Args:
        retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for delay between retries (default: 2.0)
        exceptions: Tuple of exception types to catch and retry (default: all)

    Returns:
        Decorated function that retries on transient failures

    Example:
        @retry_with_backoff(retries=3, exceptions=(ServiceUnavailable,))
        def upload_file():
            # ... upload logic
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            delay = 1.0
            last_exception = None

            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retries:
                        logger.error(
                            f"{func.__name__} failed after {retries} retries: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{retries}), "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                    delay *= backoff_factor

            # Should never reach here, but satisfy type checker
            if last_exception:
                raise last_exception

        return wrapper

    return decorator
