"""Tests for retry_with_backoff decorator."""

from typing import Any
from unittest.mock import Mock, call, patch

import pytest

from datawagon.bucket.retry_utils import retry_with_backoff


class TransientError(Exception):
    pass


@patch("datawagon.bucket.retry_utils.time.sleep")
def test_success_first_try_does_not_sleep(mock_sleep: Any) -> None:
    func = Mock(return_value="ok", __name__="func")
    wrapped = retry_with_backoff(retries=3)(func)

    assert wrapped(1, key="v") == "ok"
    func.assert_called_once_with(1, key="v")
    mock_sleep.assert_not_called()


@patch("datawagon.bucket.retry_utils.time.sleep")
def test_succeeds_after_retries_with_exponential_backoff(mock_sleep: Any) -> None:
    func = Mock(side_effect=[TransientError("a"), TransientError("b"), "ok"], __name__="func")
    wrapped = retry_with_backoff(retries=3, backoff_factor=3.0, exceptions=(TransientError,))(func)

    assert wrapped() == "ok"
    assert func.call_count == 3
    assert mock_sleep.call_args_list == [call(1.0), call(3.0)]


@patch("datawagon.bucket.retry_utils.time.sleep")
def test_exhausting_retries_reraises_last_exception(mock_sleep: Any) -> None:
    errors = [TransientError(str(i)) for i in range(3)]
    func = Mock(side_effect=errors, __name__="func")
    wrapped = retry_with_backoff(retries=2, exceptions=(TransientError,))(func)

    with pytest.raises(TransientError) as exc_info:
        wrapped()

    assert exc_info.value is errors[-1]
    assert func.call_count == 3  # initial attempt + 2 retries
    assert mock_sleep.call_args_list == [call(1.0), call(2.0)]


@patch("datawagon.bucket.retry_utils.time.sleep")
def test_unlisted_exception_is_not_retried(mock_sleep: Any) -> None:
    func = Mock(side_effect=ValueError("bad input"), __name__="func")
    wrapped = retry_with_backoff(retries=3, exceptions=(TransientError,))(func)

    with pytest.raises(ValueError, match="bad input"):
        wrapped()

    func.assert_called_once()
    mock_sleep.assert_not_called()


@patch("datawagon.bucket.retry_utils.time.sleep")
def test_zero_retries_raises_immediately(mock_sleep: Any) -> None:
    func = Mock(side_effect=TransientError("x"), __name__="func")
    wrapped = retry_with_backoff(retries=0, exceptions=(TransientError,))(func)

    with pytest.raises(TransientError):
        wrapped()

    func.assert_called_once()
    mock_sleep.assert_not_called()


def test_preserves_wrapped_function_metadata() -> None:
    @retry_with_backoff()
    def documented() -> int:
        """Docstring."""
        return 1

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "Docstring."
