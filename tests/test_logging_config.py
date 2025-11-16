"""Tests for logging configuration."""

import logging
import unittest

from datawagon.logging_config import get_logger, setup_logging


class TestLoggingConfig(unittest.TestCase):
    """Test cases for logging configuration."""

    def test_setup_logging_returns_logger(self) -> None:
        """Test that setup_logging returns a logger instance."""
        logger = setup_logging()
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "datawagon")

    def test_setup_logging_with_custom_level(self) -> None:
        """Test setting up logging with custom level."""
        logger = setup_logging(level="DEBUG")
        # Logger might have level 0 (NOTSET) and inherit from root
        self.assertEqual(logger.getEffectiveLevel(), logging.DEBUG)

        logger = setup_logging(level="WARNING")
        self.assertEqual(logger.getEffectiveLevel(), logging.WARNING)

    def test_get_logger_with_name(self) -> None:
        """Test getting a logger with specific name."""
        logger = get_logger("test_module")
        self.assertEqual(logger.name, "datawagon.test_module")
        self.assertIsInstance(logger, logging.Logger)

    def test_get_logger_inherits_parent_level(self) -> None:
        """Test that child loggers inherit parent configuration."""
        parent_logger = setup_logging(level="ERROR")
        child_logger = get_logger("child")

        # Child should inherit parent's effective level
        self.assertEqual(child_logger.getEffectiveLevel(), logging.ERROR)


if __name__ == "__main__":
    unittest.main()
