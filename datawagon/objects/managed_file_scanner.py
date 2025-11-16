import fnmatch
import re
from pathlib import Path
from typing import Dict, List, Optional

import toml
from pydantic import BaseModel, Field, ValidationError

from datawagon.logging_config import get_logger

from datawagon.objects.managed_file_metadata import (
    ManagedFileInput,
    ManagedFileMetadata,
)
from datawagon.objects.source_config import SourceConfig, SourceFromLocalFS


class ManagedFiles(BaseModel):
    files: List[ManagedFileMetadata] = Field(default_factory=list)
    file_selector_base_name: str


class ManagedFilesToDatabase(ManagedFiles):
    table_name: str
    table_append_or_replace: str


class ManagedFileScanner:
    """Scans for and processes files based on configuration patterns.

    Provides optimized file scanning with cached regex patterns and
    improved performance for large directory structures.
    """

    def __init__(self, csv_source_config: Path, csv_source_dir: Path) -> None:
        """Initialize the file scanner.

        Args:
            csv_source_config: Path to the source configuration file
            csv_source_dir: Directory to scan for files

        Raises:
            ValueError: If configuration validation fails
        """
        self.csv_source_dir = csv_source_dir
        self.logger = get_logger("file_scanner")
        self._compiled_patterns: Dict[str, re.Pattern] = {}

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
        all_csv_files = self.find_files(
            source_path, glob_pat, exclude_pattern, file_extension
        )

        file_names = [str(file) for file in all_csv_files]

        return [Path(file) for file in file_names]

    def find_files(
        self,
        base_path: Path,
        match_pattern: str,
        exclude_pattern: Optional[str],
        file_extension: Optional[str] = None,
    ) -> List[Path]:
        """Find files matching the specified patterns.

        Uses optimized pattern matching and excludes system lock files.

        Args:
            base_path: Directory to search in
            match_pattern: Pattern to match filenames against
            exclude_pattern: Pattern to exclude from results
            file_extension: File extension to filter by

        Returns:
            List of matching file paths
        """
        matches = []

        # Build the full match pattern
        if file_extension is not None:
            full_match_pattern = f"*{match_pattern.lower()}*{file_extension}"
        else:
            full_match_pattern = f"*{match_pattern.lower()}*"

        exclude_pattern_lower = exclude_pattern.lower() if exclude_pattern else None
        self.logger.debug(f"Scanning {base_path} with pattern: {full_match_pattern}")

        # Use pathlib for more efficient file iteration
        try:
            for file_path in base_path.rglob("*"):
                if file_path.is_file():
                    filename_lower = file_path.name.lower()

                    # Skip system lock files early
                    if filename_lower.startswith(".~lock"):
                        continue

                    # Check match pattern
                    if fnmatch.fnmatch(filename_lower, full_match_pattern):
                        # Check exclude pattern
                        if exclude_pattern_lower and fnmatch.fnmatch(
                            filename_lower, f"*{exclude_pattern_lower}*"
                        ):
                            continue

                        matches.append(file_path)
        except PermissionError as e:
            self.logger.warning(f"Permission denied accessing {base_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error scanning directory {base_path}: {e}")

        self.logger.info(
            f"Found {len(matches)} files matching pattern '{match_pattern}'"
        )
        return matches

    def source_file_attrs(
        self,
        file_path: Path,
        file_source: SourceFromLocalFS,
        is_replace_override: bool = False,
    ) -> ManagedFileInput:
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

            # Use cached compiled pattern for better performance
            pattern_key = str(r_pattern)
            if pattern_key not in self._compiled_patterns:
                self._compiled_patterns[pattern_key] = re.compile(r_pattern)

            compiled_pattern = self._compiled_patterns[pattern_key]
            match = compiled_pattern.match(file_path.name)

            if not match:
                raise ValueError(f"Invalid file name format: {file_path}")

            if len(r_groups) != len(match.groups()):
                raise ValueError(
                    "File regex config generated mismatched groups."
                    + f"\nFile name: {file_path.name}, regex: {r_pattern}, groups: {r_groups}"
                )

            for i, group_name in enumerate(r_groups):
                file_dict[group_name] = match.group(i + 1)

        return ManagedFileInput(**file_dict)

    def matched_files(
        self, file_extension: str | None = None
    ) -> List[ManagedFilesToDatabase]:
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

        return all_available_files

    def matched_file(
        self,
        source_file_path: Path,
        input_file_base_name: str,
        is_replace_override: bool,
    ) -> ManagedFilesToDatabase | None:
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
