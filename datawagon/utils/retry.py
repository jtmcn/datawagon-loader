"""Retry utility functions for handling transient failures."""

import time
from functools import wraps
from typing import Any, Callable, Tuple, Type, TypeVar, Union

from datawagon.logging_config import get_logger

logger = get_logger("retry")

F = TypeVar("F", bound=Callable[..., Any])


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
) -> Callable[[F], F]:
    """Decorator to retry a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exceptions: Exception types to catch and retry on

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries. "
                            f"Last error: {e}"
                        )
                        raise

                    delay = min(base_delay * (2**attempt), max_delay)
                    logger.warning(
                        f"Function {func.__name__} failed on attempt {attempt + 1}/{max_retries + 1}. "
                        f"Retrying in {delay:.1f}s. Error: {e}"
                    )
                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper  # type: ignore

    return decorator
