"""Tests for logging configuration."""
import logging
from pathlib import Path

import pytest

from datawagon.logging_config import get_logger, setup_logging


@pytest.mark.unit
class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_default(self) -> None:
        """Test setup_logging with default parameters."""
        logger = setup_logging()

        assert logger.name == "datawagon"
        assert logger.level == logging.INFO

    def test_setup_logging_verbose(self) -> None:
        """Test setup_logging with verbose mode."""
        logger = setup_logging(verbose=True)

        assert logger.level == logging.DEBUG

    def test_setup_logging_with_log_file(self, temp_dir: Path) -> None:
        """Test setup_logging with log file."""
        log_file = temp_dir / "test.log"

        logger = setup_logging(log_file=str(log_file))

        assert logger.name == "datawagon"
        # Log file handler should be added
        assert len(logger.handlers) >= 2  # Console + File


@pytest.mark.unit
class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger(self) -> None:
        """Test getting a logger for a module."""
        logger = get_logger("test_module")

        assert logger.name == "datawagon.test_module"

    def test_get_logger_different_modules(self) -> None:
        """Test getting loggers for different modules."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1.name == "datawagon.module1"
        assert logger2.name == "datawagon.module2"
        assert logger1.name != logger2.name
