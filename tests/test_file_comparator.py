"""Tests for FileComparator class."""

from pathlib import Path
from typing import List

import pytest

from datawagon.objects.current_table_data import CurrentDestinationData
from datawagon.objects.file_comparator import FileComparator
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import ManagedFilesToDatabase


@pytest.mark.unit
class TestFileComparatorInit:
    """Test FileComparator initialization."""

    def test_init_creates_file_utils(self) -> None:
        """Test that FileComparator initializes with FileUtils instance."""
        comparator = FileComparator()
        assert comparator.file_utils is not None


@pytest.mark.unit
class TestCompareFiles:
    """Test FileComparator.compare_files() method."""

    def test_compare_files_empty_local_files(self) -> None:
        """Test compare_files with empty local files list."""
        comparator = FileComparator()
        local_files: List[ManagedFileMetadata] = []
        bucket_files = [
            CurrentDestinationData(base_name="claim_raw", file_count=5, source_files=["file1.csv", "file2.csv"])
        ]

        result = comparator.compare_files(local_files, bucket_files)

        assert len(result) == 1
        assert result.iloc[0]["Base Name"] == "claim_raw"
        assert result.iloc[0]["DB File Count"] == 5
        assert result.iloc[0]["Source File Count"] == 0

    def test_compare_files_empty_bucket_files(self, tmp_path: Path) -> None:
        """Test compare_files with empty bucket files list."""
        comparator = FileComparator()

        # Create mock local files
        file1 = tmp_path / "file1.csv"
        file1.touch()
        local_files = [
            ManagedFileMetadata(
                file_path=file1,
                file_dir=str(tmp_path),
                file_name="file1.csv",
                file_version="",
                base_name="claim_raw",
                table_name="claim_raw",
                file_size_in_bytes=100,
                file_size="100 B",
                table_append_or_replace="append",
                report_date_key=None,
                report_date_str=None,
                content_owner=None,
                storage_folder_name="claim_raw",
            )
        ]
        bucket_files: List[CurrentDestinationData] = []

        result = comparator.compare_files(local_files, bucket_files)

        assert len(result) == 1
        assert result.iloc[0]["Base Name"] == "claim_raw"
        assert result.iloc[0]["DB File Count"] == 0
        assert result.iloc[0]["Source File Count"] == 1

    def test_compare_files_matching_files(self, tmp_path: Path) -> None:
        """Test compare_files with matching files in both locations."""
        comparator = FileComparator()

        # Create mock local files
        file1 = tmp_path / "file1.csv"
        file1.touch()
        local_files = [
            ManagedFileMetadata(
                file_path=file1,
                file_dir=str(tmp_path),
                file_name="file1.csv",
                file_version="",
                base_name="claim_raw",
                table_name="claim_raw",
                file_size_in_bytes=100,
                file_size="100 B",
                table_append_or_replace="append",
                report_date_key=None,
                report_date_str=None,
                content_owner=None,
                storage_folder_name="claim_raw",
            )
        ]
        bucket_files = [CurrentDestinationData(base_name="claim_raw", file_count=3, source_files=["file1.csv"])]

        result = comparator.compare_files(local_files, bucket_files)

        assert len(result) == 1
        assert result.iloc[0]["Base Name"] == "claim_raw"
        assert result.iloc[0]["DB File Count"] == 3
        assert result.iloc[0]["Source File Count"] == 1

    def test_compare_files_multiple_base_names(self, tmp_path: Path) -> None:
        """Test compare_files with multiple base names."""
        comparator = FileComparator()

        # Create mock local files with different base names
        file1 = tmp_path / "file1.csv"
        file2 = tmp_path / "file2.csv"
        file1.touch()
        file2.touch()
        local_files = [
            ManagedFileMetadata(
                file_path=file1,
                file_dir=str(tmp_path),
                file_name="file1.csv",
                file_version="",
                base_name="claim_raw",
                table_name="claim_raw",
                file_size_in_bytes=100,
                file_size="100 B",
                table_append_or_replace="append",
                report_date_key=None,
                report_date_str=None,
                content_owner=None,
                storage_folder_name="claim_raw",
            ),
            ManagedFileMetadata(
                file_path=file2,
                file_dir=str(tmp_path),
                file_name="file2.csv",
                file_version="",
                base_name="revenue_summary",
                table_name="revenue_summary",
                file_size_in_bytes=200,
                file_size="200 B",
                table_append_or_replace="append",
                report_date_key=None,
                report_date_str=None,
                content_owner=None,
                storage_folder_name="revenue_summary",
            ),
        ]
        bucket_files = [
            CurrentDestinationData(base_name="claim_raw", file_count=5, source_files=["file1.csv"]),
            CurrentDestinationData(base_name="revenue_summary", file_count=3, source_files=["file2.csv"]),
        ]

        result = comparator.compare_files(local_files, bucket_files)

        assert len(result) == 2
        # Results should be sorted by Base Name
        assert result.iloc[0]["Base Name"] == "claim_raw"
        assert result.iloc[1]["Base Name"] == "revenue_summary"

    def test_compare_files_sorted_by_base_name(self, tmp_path: Path) -> None:
        """Test that compare_files returns DataFrame sorted by Base Name."""
        comparator = FileComparator()

        # Create files with base names in non-alphabetical order
        file1 = tmp_path / "file1.csv"
        file2 = tmp_path / "file2.csv"
        file1.touch()
        file2.touch()
        local_files = [
            ManagedFileMetadata(
                file_path=file1,
                file_dir=str(tmp_path),
                file_name="file1.csv",
                file_version="",
                base_name="zebra_data",
                table_name="zebra_data",
                file_size_in_bytes=100,
                file_size="100 B",
                table_append_or_replace="append",
                report_date_key=None,
                report_date_str=None,
                content_owner=None,
                storage_folder_name="zebra_data",
            ),
            ManagedFileMetadata(
                file_path=file2,
                file_dir=str(tmp_path),
                file_name="file2.csv",
                file_version="",
                base_name="apple_data",
                table_name="apple_data",
                file_size_in_bytes=200,
                file_size="200 B",
                table_append_or_replace="append",
                report_date_key=None,
                report_date_str=None,
                content_owner=None,
                storage_folder_name="apple_data",
            ),
        ]
        bucket_files: List[CurrentDestinationData] = []

        result = comparator.compare_files(local_files, bucket_files)

        # Should be sorted alphabetically
        assert result.iloc[0]["Base Name"] == "apple_data"
        assert result.iloc[1]["Base Name"] == "zebra_data"


@pytest.mark.unit
class TestFindNewFiles:
    """Test FileComparator.find_new_files() method."""

    def test_find_new_files_all_new(self, tmp_path: Path) -> None:
        """Test find_new_files when all local files are new."""
        comparator = FileComparator()

        # Create mock local files
        file1 = tmp_path / "file1.csv"
        file2 = tmp_path / "file2.csv"
        file1.touch()
        file2.touch()
        local_file1 = ManagedFileMetadata(
            file_path=file1,
            file_dir=str(tmp_path),
            file_name="file1.csv",
            file_version="",
            base_name="claim_raw",
            table_name="claim_raw",
            file_size_in_bytes=100,
            file_size="100 B",
            table_append_or_replace="append",
            report_date_key=None,
            report_date_str=None,
            content_owner=None,
            storage_folder_name="claim_raw",
        )
        local_file2 = ManagedFileMetadata(
            file_path=file2,
            file_dir=str(tmp_path),
            file_name="file2.csv",
            file_version="",
            base_name="claim_raw",
            table_name="claim_raw",
            file_size_in_bytes=200,
            file_size="200 B",
            table_append_or_replace="append",
            report_date_key=None,
            report_date_str=None,
            content_owner=None,
            storage_folder_name="claim_raw",
        )
        local_groups = [
            ManagedFilesToDatabase(
                files=[local_file1, local_file2],
                file_selector_base_name="claim_raw",
                table_name="claim_raw",
                table_append_or_replace="append",
            )
        ]
        bucket_files: List[CurrentDestinationData] = []

        result = comparator.find_new_files(local_groups, bucket_files)

        assert len(result) == 1
        assert len(result[0].files) == 2

    def test_find_new_files_no_new(self, tmp_path: Path) -> None:
        """Test find_new_files when no files are new."""
        comparator = FileComparator()

        # Create mock local files
        file1 = tmp_path / "file1.csv"
        file1.touch()
        local_file1 = ManagedFileMetadata(
            file_path=file1,
            file_dir=str(tmp_path),
            file_name="file1.csv",
            file_version="",
            base_name="claim_raw",
            table_name="claim_raw",
            file_size_in_bytes=100,
            file_size="100 B",
            table_append_or_replace="append",
            report_date_key=None,
            report_date_str=None,
            content_owner=None,
            storage_folder_name="claim_raw",
        )
        local_groups = [
            ManagedFilesToDatabase(
                files=[local_file1],
                file_selector_base_name="claim_raw",
                table_name="claim_raw",
                table_append_or_replace="append",
            )
        ]
        bucket_files = [CurrentDestinationData(base_name="claim_raw", file_count=1, source_files=["file1.csv"])]

        result = comparator.find_new_files(local_groups, bucket_files)

        assert len(result) == 1
        assert len(result[0].files) == 0  # All files filtered out

    def test_find_new_files_partial_overlap(self, tmp_path: Path) -> None:
        """Test find_new_files with partial overlap."""
        comparator = FileComparator()

        # Create mock local files
        file1 = tmp_path / "file1.csv"
        file2 = tmp_path / "file2.csv"
        file3 = tmp_path / "file3.csv"
        file1.touch()
        file2.touch()
        file3.touch()
        local_file1 = ManagedFileMetadata(
            file_path=file1,
            file_dir=str(tmp_path),
            file_name="file1.csv",
            file_version="",
            base_name="claim_raw",
            table_name="claim_raw",
            file_size_in_bytes=100,
            file_size="100 B",
            table_append_or_replace="append",
            report_date_key=None,
            report_date_str=None,
            content_owner=None,
            storage_folder_name="claim_raw",
        )
        local_file2 = ManagedFileMetadata(
            file_path=file2,
            file_dir=str(tmp_path),
            file_name="file2.csv",
            file_version="",
            base_name="claim_raw",
            table_name="claim_raw",
            file_size_in_bytes=200,
            file_size="200 B",
            table_append_or_replace="append",
            report_date_key=None,
            report_date_str=None,
            content_owner=None,
            storage_folder_name="claim_raw",
        )
        local_file3 = ManagedFileMetadata(
            file_path=file3,
            file_dir=str(tmp_path),
            file_name="file3.csv",
            file_version="",
            base_name="claim_raw",
            table_name="claim_raw",
            file_size_in_bytes=300,
            file_size="300 B",
            table_append_or_replace="append",
            report_date_key=None,
            report_date_str=None,
            content_owner=None,
            storage_folder_name="claim_raw",
        )
        local_groups = [
            ManagedFilesToDatabase(
                files=[local_file1, local_file2, local_file3],
                file_selector_base_name="claim_raw",
                table_name="claim_raw",
                table_append_or_replace="append",
            )
        ]
        bucket_files = [CurrentDestinationData(base_name="claim_raw", file_count=1, source_files=["file1.csv"])]

        result = comparator.find_new_files(local_groups, bucket_files)

        assert len(result) == 1
        assert len(result[0].files) == 2  # file2 and file3 are new
        assert result[0].files[0].file_name == "file2.csv"
        assert result[0].files[1].file_name == "file3.csv"

    def test_find_new_files_empty_inputs(self) -> None:
        """Test find_new_files with empty inputs."""
        comparator = FileComparator()
        local_groups: List[ManagedFilesToDatabase] = []
        bucket_files: List[CurrentDestinationData] = []

        result = comparator.find_new_files(local_groups, bucket_files)

        assert len(result) == 0

    def test_find_new_files_sorted_by_base_name(self, tmp_path: Path) -> None:
        """Test that find_new_files returns files sorted by base_name."""
        comparator = FileComparator()

        # Create files with different base names in non-alphabetical order
        file1 = tmp_path / "file1.csv"
        file2 = tmp_path / "file2.csv"
        file1.touch()
        file2.touch()
        local_file1 = ManagedFileMetadata(
            file_path=file1,
            file_dir=str(tmp_path),
            file_name="file1.csv",
            file_version="",
            base_name="zebra_data",
            table_name="zebra_data",
            file_size_in_bytes=100,
            file_size="100 B",
            table_append_or_replace="append",
            report_date_key=None,
            report_date_str=None,
            content_owner=None,
            storage_folder_name="zebra_data",
        )
        local_file2 = ManagedFileMetadata(
            file_path=file2,
            file_dir=str(tmp_path),
            file_name="file2.csv",
            file_version="",
            base_name="apple_data",
            table_name="apple_data",
            file_size_in_bytes=200,
            file_size="200 B",
            table_append_or_replace="append",
            report_date_key=None,
            report_date_str=None,
            content_owner=None,
            storage_folder_name="apple_data",
        )
        # Add in non-alphabetical order
        local_groups = [
            ManagedFilesToDatabase(
                files=[local_file1, local_file2],
                file_selector_base_name="test_data",
                table_name="test_data",
                table_append_or_replace="append",
            )
        ]
        bucket_files: List[CurrentDestinationData] = []

        result = comparator.find_new_files(local_groups, bucket_files)

        # Should be sorted alphabetically by base_name
        assert len(result[0].files) == 2
        assert result[0].files[0].base_name == "apple_data"
        assert result[0].files[1].base_name == "zebra_data"
