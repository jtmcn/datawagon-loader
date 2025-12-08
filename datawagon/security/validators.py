"""Security validation utilities for DataWagon."""
import logging
import os
import re
import urllib.parse
import zipfile
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when a security validation fails."""

    pass


def validate_path_traversal(
    file_path: Union[str, Path], base_dir: Union[str, Path]
) -> Path:
    """Validate that file_path is within base_dir (prevents path traversal).

    Args:
        file_path: Path to validate
        base_dir: Base directory that file_path must be within

    Returns:
        Resolved absolute Path object

    Raises:
        SecurityError: If path traversal detected

    Example:
        >>> validate_path_traversal("/tmp/test.csv", "/tmp")
        Path('/tmp/test.csv')
    """
    try:
        base = Path(base_dir).resolve()
        target = Path(file_path).resolve()

        # Check if target is relative to base
        target.relative_to(base)

        return target
    except (ValueError, RuntimeError) as e:
        raise SecurityError(
            f"Path traversal detected: {file_path} is outside {base_dir}"
        ) from e


def validate_regex_complexity(pattern: str, max_length: int = 500) -> None:
    """Validate regex pattern to prevent ReDoS attacks.

    Args:
        pattern: Regex pattern to validate
        max_length: Maximum allowed pattern length

    Raises:
        SecurityError: If pattern is suspicious

    Example:
        >>> validate_regex_complexity(r"YouTube_(.+)_M_(\\d{8})")
    """
    if len(pattern) > max_length:
        raise SecurityError(f"Regex pattern too long: {len(pattern)} > {max_length}")

    # Check for nested quantifiers (e.g., (a+)+, (a*)+, (a+)*)
    nested_quantifiers = re.findall(r"\([^)]*[+*]\)[+*]", pattern)
    if nested_quantifiers:
        raise SecurityError(
            f"Nested quantifiers detected (ReDoS risk): {nested_quantifiers}"
        )

    # Check for excessive alternation groups
    alternation_groups = pattern.count("|")
    if alternation_groups > 20:
        raise SecurityError(
            f"Too many alternation groups: {alternation_groups} (ReDoS risk)"
        )


def validate_blob_name(blob_name: str, max_length: int = 1024) -> str:
    """Validate GCS blob name with URL decode check.

    Args:
        blob_name: Blob name to validate
        max_length: Maximum allowed length

    Returns:
        Validated blob name

    Raises:
        SecurityError: If blob name is invalid or contains attacks

    Example:
        >>> validate_blob_name("folder/file.csv")
        'folder/file.csv'
    """
    if len(blob_name) > max_length:
        raise SecurityError(f"Blob name too long: {len(blob_name)} > {max_length}")

    # FIX: Detect and validate URL-encoded names to prevent bypass
    decoded = urllib.parse.unquote(blob_name)
    if decoded != blob_name:
        logger.warning(f"Blob name URL-encoded: {blob_name} -> {decoded}")
        # Recursively validate decoded version to prevent ..%2F..%2F attacks
        validate_blob_name(decoded, max_length)

    # Check for path traversal attempts
    if ".." in blob_name or blob_name.startswith("/"):
        raise SecurityError(f"Invalid blob name (path traversal): {blob_name}")

    # Check for control characters (including null bytes)
    if any(ord(c) < 32 for c in blob_name) or "\x00" in blob_name:
        raise SecurityError(f"Control characters in blob name: {blob_name}")

    return blob_name


MAX_DECOMPRESSED_SIZE = 1024 * 1024 * 1024  # 1GB


def check_zip_safety(
    file_path: Union[str, Path], max_size: int = MAX_DECOMPRESSED_SIZE
) -> None:
    """Check if a zip file is safe to extract (prevents zip bombs).

    Args:
        file_path: Path to zip file
        max_size: Maximum allowed decompressed size in bytes

    Raises:
        SecurityError: If zip file is suspicious

    Example:
        >>> check_zip_safety("/tmp/test.zip")
    """
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            total_size = sum(info.file_size for info in zf.infolist())

            if total_size > max_size:
                raise SecurityError(
                    f"Zip file decompressed size ({total_size} bytes) "
                    f"exceeds limit ({max_size} bytes)"
                )

            # Check compression ratio
            compressed_size = os.path.getsize(file_path)
            if compressed_size > 0:
                ratio = total_size / compressed_size
                if ratio > 100:  # More than 100:1 compression is suspicious
                    logger.warning(
                        f"High compression ratio: {ratio:.1f}:1 for {file_path}"
                    )
    except zipfile.BadZipFile as e:
        raise SecurityError(f"Invalid zip file: {file_path}") from e
