"""Custom exceptions for the datawagon application."""


class DatawagonError(Exception):
    """Base exception class for datawagon-specific errors."""

    pass


class ConfigurationError(DatawagonError):
    """Raised when there are configuration-related errors."""

    pass


class GcsConnectionError(DatawagonError):
    """Raised when unable to connect to Google Cloud Storage."""

    pass


class GcsOperationError(DatawagonError):
    """Raised when a GCS operation fails."""

    pass


class FileProcessingError(DatawagonError):
    """Raised when there are errors processing files."""

    pass


class ValidationError(DatawagonError):
    """Raised when data validation fails."""

    pass
