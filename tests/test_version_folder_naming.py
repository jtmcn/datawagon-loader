"""Tests for version-based folder naming functionality."""

from pathlib import Path
from unittest.mock import MagicMock

from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import (
    ManagedFileScanner,
    ManagedFilesToDatabase,
)


def test_versioned_file_gets_suffix():
    """Versioned file - always gets version suffix."""
    file1 = ManagedFileMetadata(
        file_name="test_v1-1.csv.gz",
        file_path=Path("/test/test_v1-1.csv.gz"),
        base_name="test",
        table_name="test",
        table_append_or_replace="append",
        storage_folder_name="caravan/test",
        file_dir="/test",
        content_owner="Brand",
        report_date_key=20230601,
        report_date_str="2023-06-30",
        file_version="v1-1",
        file_size_in_bytes=1000,
        file_size="1 KB",
    )

    file_group = ManagedFilesToDatabase(
        table_name="test",
        table_append_or_replace="append",
        file_selector_base_name="test",
        files=[file1],
    )

    # Create a mock scanner to test the method directly
    scanner = MagicMock(spec=ManagedFileScanner)
    ManagedFileScanner._apply_version_based_folder_naming(scanner, [file_group])

    # Versioned file always gets suffix
    assert file1.storage_folder_name == "caravan/test_v1-1"


def test_non_versioned_file_no_suffix():
    """Non-versioned file - no suffix (backward compatible)."""
    file1 = ManagedFileMetadata(
        file_name="test.csv.gz",
        file_path=Path("/test/test.csv.gz"),
        base_name="test",
        table_name="test",
        table_append_or_replace="append",
        storage_folder_name="caravan/test",
        file_dir="/test",
        content_owner="Brand",
        report_date_key=20230601,
        report_date_str="2023-06-30",
        file_version="",  # Empty version
        file_size_in_bytes=1000,
        file_size="1 KB",
    )

    file_group = ManagedFilesToDatabase(
        table_name="test",
        table_append_or_replace="append",
        file_selector_base_name="test",
        files=[file1],
    )

    # Create a mock scanner to test the method directly
    scanner = MagicMock(spec=ManagedFileScanner)
    ManagedFileScanner._apply_version_based_folder_naming(scanner, [file_group])

    # Non-versioned file - no suffix
    assert file1.storage_folder_name == "caravan/test"


def test_multiple_versions_with_suffix():
    """Multiple versions - suffix added to all."""
    file1 = ManagedFileMetadata(
        file_name="test_v1-0.csv.gz",
        file_path=Path("/test/test_v1-0.csv.gz"),
        base_name="test",
        table_name="test",
        table_append_or_replace="append",
        storage_folder_name="caravan/test",
        file_dir="/test",
        content_owner="Brand",
        report_date_key=20230601,
        report_date_str="2023-06-30",
        file_version="v1-0",
        file_size_in_bytes=1000,
        file_size="1 KB",
    )

    file2 = ManagedFileMetadata(
        file_name="test_v1-1.csv.gz",
        file_path=Path("/test/test_v1-1.csv.gz"),
        base_name="test",
        table_name="test",
        table_append_or_replace="append",
        storage_folder_name="caravan/test",
        file_dir="/test",
        content_owner="Brand",
        report_date_key=20230601,
        report_date_str="2023-06-30",
        file_version="v1-1",
        file_size_in_bytes=1000,
        file_size="1 KB",
    )

    file_group = ManagedFilesToDatabase(
        table_name="test",
        table_append_or_replace="append",
        file_selector_base_name="test",
        files=[file1, file2],
    )

    # Create a mock scanner to test the method directly
    scanner = MagicMock(spec=ManagedFileScanner)
    ManagedFileScanner._apply_version_based_folder_naming(scanner, [file_group])

    assert file1.storage_folder_name == "caravan/test_v1-0"
    assert file2.storage_folder_name == "caravan/test_v1-1"
