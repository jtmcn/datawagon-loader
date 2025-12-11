"""Tests for ManagedFileScanner."""

from pathlib import Path

import pytest
import toml

from datawagon.objects.managed_file_scanner import (
    ManagedFiles,
    ManagedFileScanner,
    ManagedFilesToDatabase,
)
from datawagon.objects.source_config import SourceConfig


@pytest.mark.unit
class TestManagedFilesModels:
    """Test ManagedFiles and ManagedFilesToDatabase models."""

    def test_create_managed_files(self) -> None:
        """Test creating ManagedFiles model."""
        managed_files = ManagedFiles(
            file_selector_base_name="YouTube_*_M",
            files=[],
        )

        assert managed_files.file_selector_base_name == "YouTube_*_M"
        assert managed_files.files == []

    def test_create_managed_files_to_database(self) -> None:
        """Test creating ManagedFilesToDatabase model."""
        db_files = ManagedFilesToDatabase(
            file_selector_base_name="YouTube_*_M",
            table_name="youtube_raw",
            table_append_or_replace="append",
            files=[],
        )

        assert db_files.file_selector_base_name == "YouTube_*_M"
        assert db_files.table_name == "youtube_raw"
        assert db_files.table_append_or_replace == "append"
        assert db_files.files == []


@pytest.mark.unit
class TestManagedFileScannerInit:
    """Test ManagedFileScanner initialization."""

    def test_init_with_valid_config(self, temp_dir: Path) -> None:
        """Test initializing scanner with valid config."""
        config_path = temp_dir / "test_config.toml"
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # Create valid config
        config = {
            "file": {
                "youtube_data": {
                    "is_enabled": True,
                    "select_file_name_base": "YouTube_*_M",
                    "exclude_file_name_base": ".~lock",
                    "regex_pattern": r"YouTube_(.+)_M_(\d{8}|\d{6})",
                    "regex_group_names": ["content_owner", "file_date_key"],
                    "storage_folder_name": "youtube_analytics",
                    "table_name": "youtube_raw",
                    "table_append_or_replace": "append",
                }
            }
        }

        with open(config_path, "w") as f:
            toml.dump(config, f)

        scanner = ManagedFileScanner(config_path, source_dir)

        assert scanner.csv_source_dir == source_dir
        assert isinstance(scanner.valid_config, SourceConfig)

    def test_init_with_invalid_config(self, temp_dir: Path) -> None:
        """Test that invalid config raises ValidationError."""
        config_path = temp_dir / "invalid_config.toml"
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # Create invalid config (missing required fields)
        config = {
            "file": {
                "youtube_data": {
                    "is_enabled": True,
                    # Missing required fields
                }
            }
        }

        with open(config_path, "w") as f:
            toml.dump(config, f)

        with pytest.raises(ValueError) as exc_info:
            ManagedFileScanner(config_path, source_dir)

        assert "Validation Failed" in str(exc_info.value)


@pytest.mark.unit
class TestFindFiles:
    """Test find_files method."""

    def test_find_files_with_match(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test finding files that match pattern."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # Create matching files
        (source_dir / "YouTube_BrandName_M_20230601_v1.csv").touch()
        (source_dir / "YouTube_OtherBrand_M_20230701_v1.csv").touch()
        (source_dir / "unrelated_file.csv").touch()

        config_path = temp_dir / "config.toml"
        config_path.write_text("")

        # Manually set valid_config to avoid TOML loading
        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        results = scanner.find_files(
            source_dir, match_pattern="YouTube_*_M", exclude_pattern=None
        )

        assert len(results) == 2
        assert all("YouTube" in str(f) for f in results)

    def test_find_files_with_extension_filter(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test finding files with specific extension."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # Create files with different extensions
        (source_dir / "YouTube_Brand_M_20230601.csv").touch()
        (source_dir / "YouTube_Brand_M_20230601.csv.gz").touch()
        (source_dir / "YouTube_Brand_M_20230601.csv.zip").touch()

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        results = scanner.find_files(
            source_dir,
            match_pattern="YouTube_*_M",
            exclude_pattern=None,
            file_extension=".csv.gz",
        )

        assert len(results) == 1
        assert results[0].suffix == ".gz"

    def test_find_files_with_exclude_pattern(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test finding files while excluding specific patterns."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # Create files
        (source_dir / "YouTube_Brand_M_20230601.csv").touch()
        (source_dir / "YouTube_Brand_M_20230601_backup.csv").touch()
        (source_dir / "YouTube_Brand_M_20230601_archive.csv").touch()

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        results = scanner.find_files(
            source_dir,
            match_pattern="YouTube_*_M",
            exclude_pattern="backup",
        )

        # Should exclude files with "backup" in name
        assert len(results) == 2
        assert not any("backup" in str(f) for f in results)

    def test_find_files_excludes_lock_files(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test that .~lock files are excluded."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # Create normal and lock files
        (source_dir / "YouTube_Brand_M_20230601.csv").touch()
        (source_dir / ".~lock.YouTube_Brand_M_20230601.csv").touch()

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        results = scanner.find_files(
            source_dir, match_pattern="YouTube_*_M", exclude_pattern=None
        )

        # Should exclude .~lock files
        assert len(results) == 1
        assert not any(".~lock" in str(f) for f in results)

    def test_find_files_in_nested_directories(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test finding files in nested directory structure."""
        source_dir = temp_dir / "source"
        nested_dir = source_dir / "subdir" / "nested"
        nested_dir.mkdir(parents=True)

        # Create files at different levels
        (source_dir / "YouTube_Brand_M_20230601.csv").touch()
        (nested_dir / "YouTube_Brand_M_20230701.csv").touch()

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        results = scanner.find_files(
            source_dir, match_pattern="YouTube_*_M", exclude_pattern=None
        )

        # Should find files at all levels
        assert len(results) == 2

    def test_find_files_empty_directory(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test finding files in empty directory."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        results = scanner.find_files(
            source_dir, match_pattern="YouTube_*_M", exclude_pattern=None
        )

        assert len(results) == 0


@pytest.mark.unit
class TestSourceFileAttrs:
    """Test source_file_attrs method."""

    def test_source_file_attrs_with_regex_groups(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test extracting file attributes with regex groups."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        file_path = source_dir / "YouTube_BrandName_M_20230601_claim_raw_v1-1.csv.gz"
        file_path.touch()

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        file_source = mock_source_config.file["youtube_data"]
        result = scanner.source_file_attrs(file_path, file_source)

        assert result.file_name == file_path.name
        assert result.file_path == file_path
        assert result.base_name == "YouTube_*_M_*"
        assert result.table_name == "youtube_raw"

        # Check extracted regex groups
        attrs_dict = result.model_dump()
        assert attrs_dict["content_owner"] == "BrandName"
        assert attrs_dict["file_date_key"] == "20230601"

    def test_source_file_attrs_with_replace_override(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test that replace override changes table_append_or_replace."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        file_path = source_dir / "YouTube_Brand_M_20230601.csv"
        file_path.touch()

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        file_source = mock_source_config.file["youtube_data"]

        # Without override (should be "append" from config)
        result_no_override = scanner.source_file_attrs(
            file_path, file_source, is_replace_override=False
        )
        assert result_no_override.table_append_or_replace == "append"

        # With override (should be "replace")
        result_with_override = scanner.source_file_attrs(
            file_path, file_source, is_replace_override=True
        )
        assert result_with_override.table_append_or_replace == "replace"

    def test_source_file_attrs_invalid_regex_match(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test that invalid file name raises ValueError."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # File name that doesn't match regex pattern
        file_path = source_dir / "invalid_file_name.csv"
        file_path.touch()

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        file_source = mock_source_config.file["youtube_data"]

        with pytest.raises(ValueError) as exc_info:
            scanner.source_file_attrs(file_path, file_source)

        assert "Invalid file name format" in str(exc_info.value)


@pytest.mark.unit
class TestApplyVersionBasedFolderNaming:
    """Test _apply_version_based_folder_naming method."""

    def test_apply_version_to_folder_name(self, youtube_file_in_temp_dir: Path) -> None:
        """Test that version is appended to storage folder name."""
        from datawagon.objects.managed_file_metadata import (
            ManagedFileInput,
            ManagedFileMetadata,
        )

        # Create file with version
        file_input = ManagedFileInput(
            file_name=youtube_file_in_temp_dir.name,
            file_path=youtube_file_in_temp_dir,
            base_name="YouTube_Brand_M",
            table_name="youtube_raw",
            table_append_or_replace="append",
            storage_folder_name="youtube_analytics",
            content_owner="BrandName",
            file_date_key="20230601",
        )

        metadata = ManagedFileMetadata.build_data_item(file_input)
        assert metadata.file_version == "v1-1"
        assert metadata.storage_folder_name == "youtube_analytics"

        # Create file group
        file_group = ManagedFilesToDatabase(
            file_selector_base_name="YouTube_*_M",
            table_name="youtube_raw",
            table_append_or_replace="append",
            files=[metadata],
        )

        # Apply version-based folder naming
        scanner = object.__new__(ManagedFileScanner)
        scanner._apply_version_based_folder_naming([file_group])

        # Should have version appended
        assert file_group.files[0].storage_folder_name == "youtube_analytics_v1-1"

    def test_no_version_leaves_folder_unchanged(self, temp_dir: Path) -> None:
        """Test that files without version don't get folder name modified."""
        from datawagon.objects.managed_file_metadata import (
            ManagedFileInput,
            ManagedFileMetadata,
        )

        # Create file without version
        file_path = temp_dir / "simple_file.csv"
        file_path.write_text("test")

        file_input = ManagedFileInput(
            file_name=file_path.name,
            file_path=file_path,
            base_name="simple_file",
            table_name="test_table",
            table_append_or_replace="append",
            storage_folder_name="test_folder",
        )

        metadata = ManagedFileMetadata.build_data_item(file_input)
        assert metadata.file_version == ""
        assert metadata.storage_folder_name == "test_folder"

        # Create file group
        file_group = ManagedFilesToDatabase(
            file_selector_base_name="simple_file",
            table_name="test_table",
            table_append_or_replace="append",
            files=[metadata],
        )

        # Apply version-based folder naming
        scanner = object.__new__(ManagedFileScanner)
        scanner._apply_version_based_folder_naming([file_group])

        # Should remain unchanged
        assert file_group.files[0].storage_folder_name == "test_folder"


@pytest.mark.unit
class TestMatchedFile:
    """Test matched_file method (single file matching)."""

    def test_matched_file_finds_by_base_name(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test finding a single file by base name."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        file_path = source_dir / "YouTube_Brand_M_20230601.csv"
        file_path.touch()

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        result = scanner.matched_file(
            file_path,
            input_file_base_name="YouTube_*_M_*",
            is_replace_override=False,
        )

        assert result is not None
        assert result.table_name == "youtube_raw"
        assert len(result.files) == 1
        assert result.files[0].file_name == file_path.name

    def test_matched_file_returns_none_for_no_match(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test that non-matching base name returns None."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        file_path = source_dir / "YouTube_Brand_M_20230601.csv"
        file_path.touch()

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        result = scanner.matched_file(
            file_path,
            input_file_base_name="NonExistentPattern",
            is_replace_override=False,
        )

        assert result is None

    def test_matched_file_with_replace_override(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test matched_file with replace override."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        file_path = source_dir / "YouTube_Brand_M_20230601.csv"
        file_path.touch()

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        result = scanner.matched_file(
            file_path,
            input_file_base_name="YouTube_*_M_*",
            is_replace_override=True,
        )

        assert result is not None
        assert result.files[0].table_append_or_replace == "replace"


@pytest.mark.integration
class TestMatchedFiles:
    """Test matched_files method (integration test)."""

    def test_matched_files_finds_all_enabled(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test that matched_files finds all files from enabled sources."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # Create matching files
        (source_dir / "YouTube_BrandName_M_20230601_claim_raw_v1-1.csv.gz").touch()
        (source_dir / "YouTube_OtherBrand_M_20230701_claim_raw_v1-0.csv.gz").touch()

        config_path = temp_dir / "config.toml"
        with open(config_path, "w") as f:
            toml.dump({"file": {}}, f)

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        results = scanner.matched_files(file_extension=".csv.gz")

        assert len(results) == 1  # One file group
        assert len(results[0].files) == 2  # Two files in the group
        assert results[0].table_name == "youtube_raw"

    def test_matched_files_applies_version_naming(
        self, temp_dir: Path, mock_source_config: SourceConfig
    ) -> None:
        """Test that matched_files applies version-based folder naming."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # Create file with version
        (source_dir / "YouTube_Brand_M_20230601_claim_v1-1.csv.gz").touch()

        config_path = temp_dir / "config.toml"
        with open(config_path, "w") as f:
            toml.dump({"file": {}}, f)

        scanner = object.__new__(ManagedFileScanner)
        scanner.csv_source_dir = source_dir
        scanner.valid_config = mock_source_config

        results = scanner.matched_files(file_extension=".csv.gz")

        # Version should be appended to folder name
        assert results[0].files[0].storage_folder_name.endswith("_v1-1")
