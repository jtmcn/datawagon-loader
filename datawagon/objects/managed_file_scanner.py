"""File scanner for discovering and processing CSV files.

This module provides the ManagedFileScanner class for scanning directories,
matching files against patterns, extracting metadata, and organizing files
for upload to GCS with version-based folder naming.
"""
import fnmatch
import os
import re
from pathlib import Path
from typing import List

import toml
from pydantic import BaseModel, Field, ValidationError

from datawagon.logging_config import get_logger
from datawagon.objects.managed_file_metadata import (
    ManagedFileInput,
    ManagedFileMetadata,
)
from datawagon.objects.source_config import SourceConfig, SourceFromLocalFS
from datawagon.security import SecurityError, validate_path_traversal

logger = get_logger(__name__)


class ManagedFiles(BaseModel):
    """Container for grouped CSV files with selector metadata.

    Groups files matched by a common pattern/selector, used as a base
    for organizing files by destination.

    Attributes:
        files: List of file metadata for matched files
        file_selector_base_name: Pattern used to select these files
    """

    files: List[ManagedFileMetadata] = Field(default_factory=list)
    file_selector_base_name: str


class ManagedFilesToDatabase(ManagedFiles):
    """Container for files grouped by destination table.

    Extends ManagedFiles with destination table information and upload strategy.

    Attributes:
        table_name: Destination table name
        table_append_or_replace: Upload strategy ("append" or "replace")
    """

    table_name: str
    table_append_or_replace: str


class ManagedFileScanner:
    """Scanner for discovering and processing CSV files based on configuration.

    Scans local filesystem for CSV files matching patterns defined in source_config.toml,
    extracts metadata using regex patterns, applies security validation, and organizes
    files for GCS upload with version-based folder naming.

    Attributes:
        csv_source_dir: Directory to scan for CSV files
        valid_config: Validated source configuration from TOML file
    """

    def __init__(self, csv_source_config: Path, csv_source_dir: Path) -> None:
        """Initialize scanner with configuration and source directory.

        Args:
            csv_source_config: Path to source_config.toml configuration file
            csv_source_dir: Directory containing CSV files to scan

        Raises:
            ValueError: If source_config.toml fails Pydantic validation
        """
        self.csv_source_dir = csv_source_dir

        try:
            source_config_file = toml.load(csv_source_config)
            self.valid_config = SourceConfig(**source_config_file)

        except ValidationError as e:
            raise ValueError(f"Validation Failed for source_config.toml\n{e}")

    def scan_for_csv_files_with_name(
        self,
        source_path: Path,
        glob_pat: str,
        exclude_pattern: str | None,
        file_extension: str | None = None,
    ) -> List[Path]:
        """Scan directory for CSV files matching pattern.

        Wrapper around find_files() that returns a list of Path objects
        for matched files.

        Args:
            source_path: Directory to search
            glob_pat: Pattern to match filenames
            exclude_pattern: Pattern to exclude files (optional)
            file_extension: Specific file extension to filter (optional)

        Returns:
            List of Path objects for matched files
        """
        all_csv_files = self.find_files(
            source_path, glob_pat, exclude_pattern, file_extension
        )

        file_names = [str(file) for file in all_csv_files]

        return [Path(file) for file in file_names]

    def find_files(
        self,
        base_path: Path,
        match_pattern: str,
        exclude_pattern: str | None,
        file_extension: str | None = None,
    ) -> List[Path]:
        """Find files matching pattern with security validation.

        Recursively searches directory tree for files matching the pattern,
        excluding files matching exclude_pattern or starting with .~lock.
        Validates all paths to prevent directory traversal attacks.

        Args:
            base_path: Root directory to search
            match_pattern: Glob pattern to match filenames
            exclude_pattern: Glob pattern to exclude files (optional)
            file_extension: Specific file extension to filter (optional)

        Returns:
            List of Path objects for matched files

        Example:
            >>> scanner.find_files(Path("/data"), "YouTube_*", ".~lock*")
            [Path('/data/YouTube_Brand_M_20230601.csv')]
        """
        matches = []

        if file_extension is not None:
            match_pattern = f"*{match_pattern.lower()}*{file_extension}"
        else:
            match_pattern = f"*{match_pattern.lower()}*"

        # FIX: Only process exclude_pattern if not None
        exclude_pattern_lower = (
            exclude_pattern.lower() if exclude_pattern is not None else None
        )

        for root, dirnames, filenames in os.walk(base_path):
            for filename in filenames:
                if fnmatch.fnmatch(filename.lower(), match_pattern):
                    # FIX: Check None before pattern matching
                    should_exclude = (
                        exclude_pattern_lower is not None
                        and fnmatch.fnmatch(
                            filename.lower(), f"*{exclude_pattern_lower}*"
                        )
                    )

                    if not should_exclude and not filename.startswith(".~lock"):
                        file_path = os.path.abspath(os.path.join(root, filename))
                        # Validate path is within base_path to prevent traversal
                        try:
                            validate_path_traversal(file_path, base_path)
                            matches.append(file_path)
                        except SecurityError as e:
                            logger.error(f"Path validation failed: {e}")
                            continue

        return [Path(match) for match in matches]

    def _apply_version_based_folder_naming(
        self, all_files: List[ManagedFilesToDatabase]
    ) -> None:
        """
        Modify storage_folder_name to include version suffix for versioned files.

        Logic:
        - If file has a version (file_version is not empty): append _{version} to storage_folder_name
        - If file has NO version (file_version is empty): leave storage_folder_name unchanged

        This ensures:
        - Each version has a stable, permanent folder (e.g., caravan/claim_raw_v1-1/)
        - Each folder maps to a single BigQuery external table
        - Backward compatible with non-versioned files (e.g., caravan/claim_raw/)

        Example outputs:
        - File with v1-1 → caravan/claim_raw_v1-1/
        - File with v1-0 → caravan/claim_raw_v1-0/
        - File with no version → caravan/claim_raw/ (unchanged)
        """
        for file_group in all_files:
            for file_metadata in file_group.files:
                # Only append version if file has one
                if file_metadata.file_version:
                    file_metadata.storage_folder_name = (
                        f"{file_metadata.storage_folder_name}_"
                        f"{file_metadata.file_version}"
                    )

    def source_file_attrs(
        self,
        file_path: Path,
        file_source: SourceFromLocalFS,
        is_replace_override: bool = False,
    ) -> ManagedFileInput:
        """Extract file attributes using regex pattern matching.

        Applies regex pattern from configuration to extract metadata fields
        from filename (e.g., content_owner, file_date_key). Creates ManagedFileInput
        with extracted attributes.

        Args:
            file_path: Path to file to process
            file_source: Source configuration with regex pattern and group names
            is_replace_override: Override table_append_or_replace to "replace"

        Returns:
            ManagedFileInput with extracted attributes

        Raises:
            ValueError: If filename doesn't match regex pattern or group count mismatch

        Example:
            >>> source = SourceFromLocalFS(regex_pattern=r"YouTube_(.+)_M_(\\d{8})", ...)
            >>> attrs = scanner.source_file_attrs(Path("YouTube_Brand_M_20230601.csv"), source)
            >>> attrs.content_owner
            'Brand'
        """
        table_append_or_replace = (
            "replace" if is_replace_override else file_source.table_append_or_replace
        )

        file_dict = {
            "file_name": file_path.name,
            "file_path": file_path,
            "base_name": file_source.select_file_name_base,
            "table_name": file_source.table_name,
            "table_append_or_replace": table_append_or_replace,
            "storage_folder_name": file_source.storage_folder_name,
        }

        if file_source.regex_pattern and file_source.regex_group_names:
            r_pattern = file_source.regex_pattern
            r_groups = file_source.regex_group_names

            match = re.match(r_pattern, file_path.name)

            if not match:
                raise ValueError(f"Invalid file name format: {file_path}")

            # Group count validation moved to config load time (source_config.py)
            # This ensures mismatches are caught early, not per-file

            for i in range(len(match.groups())):
                file_dict[r_groups[i]] = match.group(i + 1)

        return ManagedFileInput(**file_dict)

    def matched_files(
        self, file_extension: str | None = None
    ) -> List[ManagedFilesToDatabase]:
        """Scan for all files matching enabled configurations.

        Processes all enabled file sources in configuration, scans for matching
        files, extracts metadata, and groups by destination table. Applies
        version-based folder naming for versioned files.

        Args:
            file_extension: Optional file extension filter (e.g., ".csv.gz")

        Returns:
            List of ManagedFilesToDatabase objects grouped by destination

        Example:
            >>> scanner = ManagedFileScanner(config_path, source_dir)
            >>> matched = scanner.matched_files(file_extension=".csv.gz")
            >>> matched[0].table_name
            'youtube_raw'
            >>> len(matched[0].files)
            5
        """
        all_available_files: List[ManagedFilesToDatabase] = []

        valid_config = self.valid_config

        for file_id in valid_config.file:
            file_source = valid_config.file[file_id]
            if file_source.is_enabled:
                file_list = self.scan_for_csv_files_with_name(
                    self.csv_source_dir,
                    file_source.select_file_name_base,
                    file_source.exclude_file_name_base,
                    file_extension,
                )

                table_mapper = ManagedFilesToDatabase(
                    table_name=file_source.table_name
                    or file_source.select_file_name_base,
                    table_append_or_replace=file_source.table_append_or_replace,
                    file_selector_base_name=file_source.select_file_name_base,
                )

                for file_path in file_list:
                    source_file = self.source_file_attrs(file_path, file_source)
                    source_file_info = ManagedFileMetadata.build_data_item(source_file)
                    table_mapper.files.append(source_file_info)

                all_available_files.append(table_mapper)

        # Apply version-based folder naming before returning
        self._apply_version_based_folder_naming(all_available_files)

        return all_available_files

    def matched_file(
        self,
        source_file_path: Path,
        input_file_base_name: str,
        is_replace_override: bool,
    ) -> ManagedFilesToDatabase | None:
        """Process a single file matching a specific configuration.

        Finds configuration matching the base name, extracts metadata from the
        file, and creates a ManagedFilesToDatabase object for upload.

        Args:
            source_file_path: Path to file to process
            input_file_base_name: Base name pattern to match in configuration
            is_replace_override: Override table_append_or_replace to "replace"

        Returns:
            ManagedFilesToDatabase with file metadata, or None if no config matches

        Example:
            >>> result = scanner.matched_file(
            ...     Path("YouTube_Brand_M_20230601.csv"),
            ...     "YouTube_*_M_*",
            ...     is_replace_override=False
            ... )
            >>> result.table_name
            'youtube_raw'
        """
        valid_config = self.valid_config

        for file_id in valid_config.file:
            file_source = valid_config.file[file_id]
            if file_source.select_file_name_base == input_file_base_name:
                file_attrs = self.source_file_attrs(
                    source_file_path, file_source, is_replace_override
                )

                table_mapper = ManagedFilesToDatabase(
                    table_name=file_source.table_name
                    or file_source.select_file_name_base,
                    table_append_or_replace=file_source.table_append_or_replace,
                    file_selector_base_name=file_source.select_file_name_base,
                    files=[ManagedFileMetadata.build_data_item(file_attrs)],
                )
                return table_mapper

        return None
