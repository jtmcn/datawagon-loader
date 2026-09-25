"""File scanner for discovering and processing CSV files.

This module provides the ManagedFileScanner class for scanning directories,
matching files against patterns, extracting metadata, and grouping files
by Report Type.
"""

import fnmatch
import os
import re
from pathlib import Path
from typing import List

import toml
from pydantic import BaseModel, Field, ValidationError

from datawagon.logging_config import get_logger
from datawagon.objects.managed_file_metadata import ManagedFileInput, ManagedFileMetadata
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

    Extends ManagedFiles with destination table information.

    Attributes:
        table_name: Destination table name
    """

    table_name: str


class ManagedFileScanner:
    """Scanner for discovering and processing CSV files based on configuration.

    Scans local filesystem for CSV files matching patterns defined in source_config.toml,
    extracts metadata using regex patterns, applies security validation, and groups
    files by Report Type.

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
        all_csv_files = self.find_files(source_path, glob_pat, exclude_pattern, file_extension)

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
        exclude_pattern_lower = exclude_pattern.lower() if exclude_pattern is not None else None

        for root, dirnames, filenames in os.walk(base_path):
            for filename in filenames:
                if fnmatch.fnmatch(filename.lower(), match_pattern):
                    # FIX: Check None before pattern matching
                    should_exclude = exclude_pattern_lower is not None and fnmatch.fnmatch(
                        filename.lower(), f"*{exclude_pattern_lower}*"
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

    def source_file_attrs(
        self,
        file_path: Path,
        file_source: SourceFromLocalFS,
        report_type: str,
    ) -> ManagedFileInput:
        """Extract file attributes using regex pattern matching.

        Applies regex pattern from configuration to extract metadata fields
        from filename (e.g., content_owner, file_date_key). Creates ManagedFileInput
        with extracted attributes.

        Args:
            file_path: Path to file to process
            file_source: Source configuration with regex pattern and group names
            report_type: Report Type the file belongs to (the config section key)

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
        file_dict = {
            "file_name": file_path.name,
            "file_path": file_path,
            "base_name": file_source.select_file_name_base,
            "report_type": report_type,
            "table_name": file_source.table_name or report_type,
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

    def matched_files(self, file_extension: str | None = None) -> List[ManagedFilesToDatabase]:
        """Scan for all files matching enabled configurations.

        Processes all enabled file sources in configuration, scans for matching
        files, extracts metadata, and groups by Report Type.

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
                    table_name=file_source.table_name or file_source.select_file_name_base,
                    file_selector_base_name=file_source.select_file_name_base,
                )

                for file_path in file_list:
                    source_file = self.source_file_attrs(file_path, file_source, file_id)
                    source_file_info = ManagedFileMetadata.build_data_item(source_file)
                    table_mapper.files.append(source_file_info)

                all_available_files.append(table_mapper)

        return all_available_files
