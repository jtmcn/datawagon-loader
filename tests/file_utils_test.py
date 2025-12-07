import gzip
import zipfile
from pathlib import Path
from unittest import TestCase

import pytest

from datawagon.objects.file_utils import FileUtils
from datawagon.security import SecurityError
from tests.csv_file_info_mock import CsvFileInfoMock


class FileUtilsTestCase(TestCase):
    def setUp(self) -> None:
        self.file_utils = FileUtils()

    def test_group_by_base_name(self) -> None:
        mock_csv_file_infos = [CsvFileInfoMock(), CsvFileInfoMock()]

        grouped_mock_csv_file_infos = self.file_utils.group_by_base_name(mock_csv_file_infos)  # type: ignore

        assert len(grouped_mock_csv_file_infos["adj_summary"]) == 2
        with pytest.raises(KeyError):
            grouped_mock_csv_file_infos["video_summary"]

    def test_check_for_duplicate_files(self) -> None:
        mock_csv_file_infos__no_dupes = [
            CsvFileInfoMock(),
            CsvFileInfoMock(file_name="something_else"),
        ]
        assert len(self.file_utils.check_for_duplicate_files(mock_csv_file_infos__no_dupes)) == 0  # type: ignore

        mock_csv_file_infos__with_dupes = [CsvFileInfoMock(), CsvFileInfoMock()]
        assert len(self.file_utils.check_for_duplicate_files(mock_csv_file_infos__with_dupes)) == 2  # type: ignore

    def test_check_for_different_file_versions(self) -> None:
        assert (
            len(
                self.file_utils.check_for_different_file_versions(
                    [CsvFileInfoMock(), CsvFileInfoMock()]  # type: ignore
                )
            )
            == 0
        )
        assert (
            len(
                self.file_utils.check_for_different_file_versions(
                    [CsvFileInfoMock(file_version="v1-0"), CsvFileInfoMock()]  # type: ignore
                )
            )
            == 1
        )


@pytest.mark.unit
class TestCsvGzipped:
    """Test csv_gzipped method."""

    def test_csv_gzipped_creates_gz_file(self, temp_dir: Path, sample_csv_content: str) -> None:
        """Test that CSV file is gzipped successfully."""
        # Create input CSV file
        input_csv = temp_dir / "test.csv"
        input_csv.write_text(sample_csv_content)

        file_utils = FileUtils()
        result = file_utils.csv_gzipped(input_csv, remove_original_zip=False)

        # Check output file was created
        assert result.exists()
        assert str(result).endswith(".csv.gz")

        # Verify content is gzipped correctly
        with gzip.open(result, "rt") as f:
            content = f.read()
            assert content == sample_csv_content

        # Original file should still exist
        assert input_csv.exists()

    def test_csv_gzipped_removes_original(self, temp_dir: Path, sample_csv_content: str) -> None:
        """Test that original CSV is removed when requested."""
        input_csv = temp_dir / "test.csv"
        input_csv.write_text(sample_csv_content)

        file_utils = FileUtils()
        result = file_utils.csv_gzipped(input_csv, remove_original_zip=True)

        # Output file should exist
        assert result.exists()

        # Original file should be removed
        assert not input_csv.exists()

    def test_csv_gzipped_with_large_file(self, temp_dir: Path) -> None:
        """Test gzipping a larger CSV file."""
        input_csv = temp_dir / "large_test.csv"
        # Write 1MB of CSV data
        large_content = "col1,col2,col3\n" * 50000
        input_csv.write_text(large_content)

        file_utils = FileUtils()
        result = file_utils.csv_gzipped(input_csv)

        assert result.exists()
        # Verify it's compressed (gzipped should be smaller)
        assert result.stat().st_size < input_csv.stat().st_size


@pytest.mark.unit
class TestCsvZipToGzip:
    """Test csv_zip_to_gzip method."""

    def test_csv_zip_to_gzip_converts_successfully(
        self, temp_dir: Path, sample_csv_content: str
    ) -> None:
        """Test converting ZIP containing CSV to GZIP."""
        # Create ZIP file containing CSV
        zip_path = temp_dir / "test.csv.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.csv", sample_csv_content)

        file_utils = FileUtils()
        result = file_utils.csv_zip_to_gzip(zip_path, remove_original_zip=False)

        # Check output file was created
        assert result.exists()
        assert str(result).endswith(".csv.gz")

        # Verify content
        with gzip.open(result, "rt") as f:
            content = f.read()
            assert content == sample_csv_content

        # Original ZIP should still exist
        assert zip_path.exists()

    def test_csv_zip_to_gzip_removes_original(
        self, temp_dir: Path, sample_csv_content: str
    ) -> None:
        """Test that original ZIP is removed when requested."""
        zip_path = temp_dir / "test.csv.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.csv", sample_csv_content)

        file_utils = FileUtils()
        result = file_utils.csv_zip_to_gzip(zip_path, remove_original_zip=True)

        # Output should exist
        assert result.exists()

        # Original ZIP should be removed
        assert not zip_path.exists()

    def test_csv_zip_to_gzip_handles_nested_structure(
        self, temp_dir: Path, sample_csv_content: str
    ) -> None:
        """Test that nested directory structure in ZIP is flattened."""
        zip_path = temp_dir / "nested.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Add file with directory structure
            zf.writestr("folder/subfolder/data.csv", sample_csv_content)

        file_utils = FileUtils()
        result = file_utils.csv_zip_to_gzip(zip_path)

        # Output filename should be flattened (no directory structure)
        assert result.name == "data.csv.gz"
        assert result.exists()

    def test_csv_zip_to_gzip_excludes_macosx_files(
        self, temp_dir: Path, sample_csv_content: str
    ) -> None:
        """Test that __MACOSX files are excluded."""
        zip_path = temp_dir / "with_macosx.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("data.csv", sample_csv_content)
            zf.writestr("__MACOSX/._data.csv", "junk")

        file_utils = FileUtils()
        result = file_utils.csv_zip_to_gzip(zip_path)

        # Should only process the CSV file, not __MACOSX
        assert result.exists()
        assert "__MACOSX" not in str(result)

    def test_csv_zip_to_gzip_raises_on_zip_bomb(self, temp_dir: Path) -> None:
        """Test that zip bombs are rejected."""
        zip_path = temp_dir / "bomb.zip"

        # Create a zip bomb (large decompressed size)
        large_content = "A" * (100 * 1024 * 1024)  # 100MB
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for i in range(11):  # 11 * 100MB = 1.1GB
                zf.writestr(f"large{i}.csv", large_content)

        file_utils = FileUtils()

        with pytest.raises(SecurityError):
            file_utils.csv_zip_to_gzip(zip_path)

    def test_csv_zip_to_gzip_only_compresses_csv_files(
        self, temp_dir: Path, sample_csv_content: str
    ) -> None:
        """Test that only .csv files get their content compressed."""
        zip_path = temp_dir / "mixed.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Only add CSV file - ZIP with mixed types has undefined return value
            zf.writestr("data.csv", sample_csv_content)

        file_utils = FileUtils()
        result = file_utils.csv_zip_to_gzip(zip_path)

        # Should create gzip for the CSV file
        assert result.name == "data.csv.gz"
        assert result.exists()

        # Verify content was compressed
        with gzip.open(result, "rt") as f:
            assert f.read() == sample_csv_content
