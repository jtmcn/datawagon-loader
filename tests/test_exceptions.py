"""Tests for custom exceptions."""

import unittest

from datawagon.exceptions import (
    ConfigurationError,
    DatawagonError,
    FileProcessingError,
    GcsConnectionError,
    GcsOperationError,
    ValidationError,
)


class TestExceptions(unittest.TestCase):
    """Test cases for custom exception classes."""

    def test_base_exception_inheritance(self) -> None:
        """Test that all exceptions inherit from DatawagonError."""
        self.assertTrue(issubclass(ConfigurationError, DatawagonError))
        self.assertTrue(issubclass(GcsConnectionError, DatawagonError))
        self.assertTrue(issubclass(GcsOperationError, DatawagonError))
        self.assertTrue(issubclass(FileProcessingError, DatawagonError))
        self.assertTrue(issubclass(ValidationError, DatawagonError))

    def test_datawagon_error_inherits_from_exception(self) -> None:
        """Test that DatawagonError inherits from Exception."""
        self.assertTrue(issubclass(DatawagonError, Exception))

    def test_exception_instantiation(self) -> None:
        """Test that exceptions can be instantiated with messages."""
        msg = "Test error message"

        exc1 = ConfigurationError(msg)
        self.assertEqual(str(exc1), msg)

        exc2 = GcsConnectionError(msg)
        self.assertEqual(str(exc2), msg)

        exc3 = GcsOperationError(msg)
        self.assertEqual(str(exc3), msg)

    def test_exception_catching(self) -> None:
        """Test that exceptions can be caught properly."""
        with self.assertRaises(DatawagonError):
            raise ConfigurationError("Config error")

        with self.assertRaises(DatawagonError):
            raise GcsConnectionError("Connection error")

        # Test specific exception catching
        with self.assertRaises(GcsOperationError):
            raise GcsOperationError("Operation failed")

    def test_exception_chaining(self) -> None:
        """Test exception chaining with from clause."""
        original_error = ValueError("Original error")

        try:
            raise GcsConnectionError("Connection failed") from original_error
        except GcsConnectionError as e:
            self.assertEqual(str(e), "Connection failed")
            self.assertIs(e.__cause__, original_error)


if __name__ == "__main__":
    unittest.main()
