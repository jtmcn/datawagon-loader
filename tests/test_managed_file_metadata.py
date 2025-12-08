"""Tests for ManagedFileMetadata."""
from datetime import date
from pathlib import Path

import pytest

from datawagon.objects.managed_file_metadata import (ManagedFileInput,
                                                     ManagedFileMetadata)


@pytest.mark.unit
class TestManagedFileInput:
    """Test ManagedFileInput model."""

    def test_create_basic_file_input(self, temp_dir: Path) -> None:
        """Test creating a basic ManagedFileInput."""
        file_path = temp_dir / "test.csv"
        file_path.touch()

        file_input = ManagedFileInput(
            file_name="test.csv",
            file_path=file_path,
            base_name="test",
            table_name="test_table",
            table_append_or_replace="append",
            storage_folder_name="test_folder",
        )

        assert file_input.file_name == "test.csv"
        assert file_input.file_path == file_path
        assert file_input.base_name == "test"
        assert file_input.table_name == "test_table"
        assert file_input.table_append_or_replace == "append"
        assert file_input.storage_folder_name == "test_folder"

    def test_file_input_allows_extra_fields(self, temp_dir: Path) -> None:
        """Test that ManagedFileInput allows extra fields (Config.extra='allow')."""
        file_path = temp_dir / "test.csv"
        file_path.touch()

        file_input = ManagedFileInput(
            file_name="test.csv",
            file_path=file_path,
            base_name="test",
            table_name="test_table",
            table_append_or_replace="append",
            storage_folder_name="test_folder",
            # Extra fields from regex groups
            content_owner="BrandName",
            file_date_key="20230601",
        )

        # Extra fields should be accessible
        assert file_input.model_dump()["content_owner"] == "BrandName"
        assert file_input.model_dump()["file_date_key"] == "20230601"


@pytest.mark.unit
class TestDateKeyToDate:
    """Test date_key_to_date static method."""

    def test_yyyymmdd_format(self) -> None:
        """Test converting YYYYMMDD format (8 digits)."""
        result = ManagedFileMetadata.date_key_to_date(20230615)
        assert result == date(2023, 6, 15)

    def test_yyyymm_format(self) -> None:
        """Test converting YYYYMM format (6 digits) - day defaults to 1."""
        result = ManagedFileMetadata.date_key_to_date(202306)
        assert result == date(2023, 6, 1)

    def test_different_months(self) -> None:
        """Test various month values."""
        assert ManagedFileMetadata.date_key_to_date(20230101) == date(2023, 1, 1)
        assert ManagedFileMetadata.date_key_to_date(20231231) == date(2023, 12, 31)

    def test_leap_year(self) -> None:
        """Test leap year date."""
        result = ManagedFileMetadata.date_key_to_date(20240229)
        assert result == date(2024, 2, 29)


@pytest.mark.unit
class TestGetFileVersion:
    """Test get_file_version static method."""

    def test_file_with_version_hyphen(self) -> None:
        """Test extracting version with hyphen (e.g., v1-0)."""
        filename = "YouTube_BrandName_M_20230601_claim_raw_v1-1.csv.gz"
        result = ManagedFileMetadata.get_file_version(filename)
        assert result == "v1-1"

    def test_file_with_version_single_digit(self) -> None:
        """Test extracting version with single digit (e.g., v2)."""
        filename = "data_file_v2.csv"
        result = ManagedFileMetadata.get_file_version(filename)
        assert result == "v2"

    def test_file_with_version_multiple_digits(self) -> None:
        """Test extracting version with multiple digits (e.g., v10)."""
        filename = "data_file_v10.csv"
        result = ManagedFileMetadata.get_file_version(filename)
        assert result == "v10"

    def test_file_without_version(self) -> None:
        """Test file without version returns empty string."""
        filename = "data_file.csv"
        result = ManagedFileMetadata.get_file_version(filename)
        assert result == ""

    def test_file_with_multiple_versions(self) -> None:
        """Test file with multiple version patterns (should return first)."""
        filename = "data_v1_backup_v2.csv"
        result = ManagedFileMetadata.get_file_version(filename)
        assert result == "v1"


@pytest.mark.unit
class TestHumanReadableSize:
    """Test human_readable_size static method."""

    def test_bytes(self) -> None:
        """Test size in bytes."""
        assert ManagedFileMetadata.human_readable_size(100) == "100.00 B"

    def test_kilobytes(self) -> None:
        """Test size in kilobytes."""
        assert ManagedFileMetadata.human_readable_size(2048) == "2.00 KB"

    def test_megabytes(self) -> None:
        """Test size in megabytes."""
        assert ManagedFileMetadata.human_readable_size(5 * 1024 * 1024) == "5.00 MB"

    def test_gigabytes(self) -> None:
        """Test size in gigabytes."""
        assert (
            ManagedFileMetadata.human_readable_size(3 * 1024 * 1024 * 1024) == "3.00 GB"
        )

    def test_terabytes(self) -> None:
        """Test size in terabytes."""
        assert (
            ManagedFileMetadata.human_readable_size(2 * 1024 * 1024 * 1024 * 1024)
            == "2.00 TB"
        )

    def test_petabytes(self) -> None:
        """Test size in petabytes."""
        assert (
            ManagedFileMetadata.human_readable_size(
                1 * 1024 * 1024 * 1024 * 1024 * 1024
            )
            == "1.00 PB"
        )

    def test_zero_bytes(self) -> None:
        """Test zero bytes."""
        assert ManagedFileMetadata.human_readable_size(0) == "0.00 B"

    def test_fractional_kb(self) -> None:
        """Test fractional kilobytes."""
        assert ManagedFileMetadata.human_readable_size(1536) == "1.50 KB"


@pytest.mark.unit
class TestBuildDataItem:
    """Test build_data_item class method."""

    def test_build_with_all_fields(self, temp_dir: Path) -> None:
        """Test building ManagedFileMetadata with all fields."""
        # Create a test file
        file_path = temp_dir / "YouTube_BrandName_M_20230601_claim_raw_v1-1.csv.gz"
        file_path.write_text("test content")

        source_file = ManagedFileInput(
            file_name=file_path.name,
            file_path=file_path,
            base_name="YouTube_BrandName_M",
            table_name="youtube_raw",
            table_append_or_replace="append",
            storage_folder_name="youtube_analytics",
            content_owner="BrandName",
            file_date_key="20230601",
        )

        result = ManagedFileMetadata.build_data_item(source_file)

        # Check basic fields
        assert result.file_name == file_path.name
        assert result.file_path == file_path
        assert result.file_dir == str(temp_dir)
        assert result.base_name == "YouTube_BrandName_M"
        assert result.table_name == "youtube_raw"
        assert result.table_append_or_replace == "append"
        assert result.storage_folder_name == "youtube_analytics"

        # Check extracted fields
        assert result.file_version == "v1-1"
        assert result.content_owner == "BrandName"
        assert result.file_size_in_bytes > 0
        assert "B" in result.file_size  # Human readable size

        # Check date conversion (YYYYMMDD -> month end)
        assert result.report_date_str == "2023-06-30"  # June has 30 days
        assert result.report_date_key == 20230630

    def test_build_with_yyyymm_date_format(self, temp_dir: Path) -> None:
        """Test building with YYYYMM date format (6 digits)."""
        file_path = temp_dir / "data_file.csv"
        file_path.write_text("test")

        source_file = ManagedFileInput(
            file_name=file_path.name,
            file_path=file_path,
            base_name="data_file",
            table_name="test_table",
            table_append_or_replace="append",
            storage_folder_name="test_folder",
            file_date_key="202302",  # February 2023
        )

        result = ManagedFileMetadata.build_data_item(source_file)

        # February 2023 has 28 days (not a leap year)
        assert result.report_date_str == "2023-02-28"
        assert result.report_date_key == 20230228

    def test_build_with_leap_year_february(self, temp_dir: Path) -> None:
        """Test building with February in a leap year."""
        file_path = temp_dir / "data_file.csv"
        file_path.write_text("test")

        source_file = ManagedFileInput(
            file_name=file_path.name,
            file_path=file_path,
            base_name="data_file",
            table_name="test_table",
            table_append_or_replace="append",
            storage_folder_name="test_folder",
            file_date_key="202402",  # February 2024 (leap year)
        )

        result = ManagedFileMetadata.build_data_item(source_file)

        # February 2024 has 29 days (leap year)
        assert result.report_date_str == "2024-02-29"
        assert result.report_date_key == 20240229

    def test_build_without_file_date_key(self, temp_dir: Path) -> None:
        """Test building without file_date_key."""
        file_path = temp_dir / "simple_file.csv"
        file_path.write_text("test")

        source_file = ManagedFileInput(
            file_name=file_path.name,
            file_path=file_path,
            base_name="simple_file",
            table_name="test_table",
            table_append_or_replace="replace",
            storage_folder_name="test_folder",
        )

        result = ManagedFileMetadata.build_data_item(source_file)

        # Without file_date_key, date fields should be None
        assert result.report_date_str is None
        assert result.report_date_key is None

    def test_build_without_content_owner(self, temp_dir: Path) -> None:
        """Test building without content_owner."""
        file_path = temp_dir / "data_file.csv"
        file_path.write_text("test")

        source_file = ManagedFileInput(
            file_name=file_path.name,
            file_path=file_path,
            base_name="data_file",
            table_name="test_table",
            table_append_or_replace="append",
            storage_folder_name="test_folder",
            file_date_key="20230601",
        )

        result = ManagedFileMetadata.build_data_item(source_file)

        # Without content_owner, should be None
        assert result.content_owner is None

    def test_build_with_empty_storage_folder_name(self, temp_dir: Path) -> None:
        """Test building with empty storage_folder_name (should use base_name)."""
        file_path = temp_dir / "data_file.csv"
        file_path.write_text("test")

        source_file = ManagedFileInput(
            file_name=file_path.name,
            file_path=file_path,
            base_name="data_file",
            table_name="test_table",
            table_append_or_replace="append",
            storage_folder_name="",  # Empty string
        )

        result = ManagedFileMetadata.build_data_item(source_file)

        # Should fallback to base_name when empty
        assert result.storage_folder_name == "data_file"

    def test_build_with_file_without_version(self, temp_dir: Path) -> None:
        """Test building with file that has no version."""
        file_path = temp_dir / "data_file.csv"
        file_path.write_text("test")

        source_file = ManagedFileInput(
            file_name=file_path.name,
            file_path=file_path,
            base_name="data_file",
            table_name="test_table",
            table_append_or_replace="append",
            storage_folder_name="test_folder",
        )

        result = ManagedFileMetadata.build_data_item(source_file)

        # File without version should have empty string
        assert result.file_version == ""

    def test_build_with_december(self, temp_dir: Path) -> None:
        """Test building with December (31 days)."""
        file_path = temp_dir / "data_file.csv"
        file_path.write_text("test")

        source_file = ManagedFileInput(
            file_name=file_path.name,
            file_path=file_path,
            base_name="data_file",
            table_name="test_table",
            table_append_or_replace="append",
            storage_folder_name="test_folder",
            file_date_key="202312",  # December 2023
        )

        result = ManagedFileMetadata.build_data_item(source_file)

        # December has 31 days
        assert result.report_date_str == "2023-12-31"
        assert result.report_date_key == 20231231

    def test_file_size_calculation(self, temp_dir: Path) -> None:
        """Test that file size is calculated correctly."""
        file_path = temp_dir / "size_test.csv"
        # Write exactly 2KB of content
        file_path.write_text("A" * 2048)

        source_file = ManagedFileInput(
            file_name=file_path.name,
            file_path=file_path,
            base_name="size_test",
            table_name="test_table",
            table_append_or_replace="append",
            storage_folder_name="test_folder",
        )

        result = ManagedFileMetadata.build_data_item(source_file)

        assert result.file_size_in_bytes == 2048
        assert result.file_size == "2.00 KB"
