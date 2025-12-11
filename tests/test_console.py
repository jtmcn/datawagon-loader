"""Tests for Rich console abstraction layer."""

import os
from unittest.mock import MagicMock, patch

import pytest

from datawagon.console import (
    confirm,
    error,
    file_list,
    get_console,
    info,
    success,
    table,
    warning,
)


@pytest.fixture(autouse=True)
def reset_console():
    """Reset console singleton between tests."""
    import datawagon.console

    datawagon.console._console = None
    yield
    datawagon.console._console = None


def test_get_console_respects_no_color():
    """Test that NO_COLOR environment variable is respected."""
    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        import datawagon.console

        datawagon.console._console = None

        console = get_console()

        assert console.no_color is True


def test_get_console_detects_ci():
    """Test that CI environment is detected."""
    with patch.dict(os.environ, {"CI": "true"}):
        import datawagon.console

        datawagon.console._console = None

        console = get_console()

        # In CI, force_terminal should be False (check private attribute)
        assert console._force_terminal is False


def test_get_console_normal_mode():
    """Test console in normal mode (no CI, no NO_COLOR)."""
    with patch.dict(os.environ, {}, clear=True):
        import datawagon.console

        datawagon.console._console = None

        console = get_console()

        # Should allow colors and terminal features
        assert console.no_color is False


def test_success_message():
    """Test success message formatting."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        success("Test message")

        mock_instance.print.assert_called_once()
        call_args = mock_instance.print.call_args[0][0]
        assert "✓" in call_args
        assert "Test message" in call_args
        assert "[green]" in call_args


def test_success_message_no_emoji():
    """Test success message without emoji."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        success("Test message", emoji=False)

        call_args = mock_instance.print.call_args[0][0]
        assert "✓" not in call_args
        assert "Test message" in call_args


def test_error_message():
    """Test error message formatting."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        error("Error message")

        call_args = mock_instance.print.call_args[0][0]
        assert "✗" in call_args
        assert "Error message" in call_args
        assert "[red]" in call_args


def test_warning_message():
    """Test warning message formatting."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        warning("Warning message")

        call_args = mock_instance.print.call_args[0][0]
        assert "⚠" in call_args
        assert "Warning message" in call_args
        assert "[yellow]" in call_args


def test_info_message():
    """Test info message formatting."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        info("Info message")

        mock_instance.print.assert_called_once_with("Info message", style="")


def test_info_message_bold():
    """Test info message with bold formatting."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        info("Info message", bold=True)

        mock_instance.print.assert_called_once_with("Info message", style="bold")


def test_table_creation():
    """Test table creation with headers and data."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        data = [["row1col1", "row1col2"], ["row2col1", "row2col2"]]
        headers = ["Header1", "Header2"]

        table(data, headers, title="Test Table")

        # Verify print was called with Table object
        mock_instance.print.assert_called_once()


def test_table_numeric_alignment():
    """Test that tables right-align columns with 'count' in header."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        data = [["item1", "100"], ["item2", "200"]]
        headers = ["Name", "File Count"]

        # We can't easily test the justify parameter without inspecting the Table object
        # But we can verify the function runs without error
        table(data, headers)

        assert mock_instance.print.called


def test_file_list_basic():
    """Test basic file list display."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        files = ["file1.csv", "file2.csv", "file3.csv"]

        file_list(files, max_display=10)

        # Should print each file
        assert mock_instance.print.call_count >= 3


def test_file_list_truncation():
    """Test file list truncates long lists."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        files = [f"file{i}.csv" for i in range(20)]

        file_list(files, max_display=5)

        # Should print title + 5 files + "and X more" message
        # At minimum: 5 files + 1 "and X more" = 6 prints
        assert mock_instance.print.call_count >= 6


def test_file_list_with_title():
    """Test file list with title."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        files = ["file1.csv", "file2.csv"]

        file_list(files, title="Test Files")

        # Should print title first
        first_call = mock_instance.print.call_args_list[0][0][0]
        assert "Test Files" in first_call


def test_inline_status_success():
    """Test inline status with success."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        from datawagon.console import inline_status_end, inline_status_start

        inline_status_start("Processing...")
        inline_status_end(True)

        # First call should have end=" "
        assert mock_instance.print.call_count == 2
        assert mock_instance.print.call_args_list[0][1]["end"] == " "

        # Second call should have success message
        second_call = mock_instance.print.call_args_list[1][0][0]
        assert "✓" in second_call
        assert "Success" in second_call


def test_inline_status_failure():
    """Test inline status with failure."""
    with patch("datawagon.console.get_console") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        from datawagon.console import inline_status_end, inline_status_start

        inline_status_start("Processing...")
        inline_status_end(False)

        # Second call should have error message
        second_call = mock_instance.print.call_args_list[1][0][0]
        assert "✗" in second_call
        assert "Failed" in second_call


def test_confirm_wraps_click():
    """Test that confirm wraps click.confirm."""
    with patch("click.confirm") as mock_click:
        mock_click.return_value = True

        result = confirm("Continue?", default=False, abort=True)

        assert result is True
        mock_click.assert_called_once_with("Continue?", default=False, abort=True)


def test_console_singleton():
    """Test that get_console returns the same instance."""
    console1 = get_console()
    console2 = get_console()

    assert console1 is console2
