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
    files: List[ManagedFileMetadata] = Field(default_factory=list)
    file_selector_base_name: str


class ManagedFilesToDatabase(ManagedFiles):
    table_name: str
    table_append_or_replace: str


class ManagedFileScanner:
    def __init__(self, csv_source_config: Path, csv_source_dir: Path) -> None:
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
        matches = []

        if file_extension is not None:
            match_pattern = f"*{match_pattern.lower()}*{file_extension}"
        else:
            match_pattern = f"*{match_pattern.lower()}*"

        if exclude_pattern is not None:
            exclude_pattern = exclude_pattern.lower()

        for root, dirnames, filenames in os.walk(base_path):
            for filename in filenames:
                if fnmatch.fnmatch(filename.lower(), match_pattern):
                    if not fnmatch.fnmatch(filename.lower(), f"*{exclude_pattern}*"):
                        if not filename.startswith(".~lock"):
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
                        f"{file_metadata.storage_folder_name}_{file_metadata.file_version}"
                    )

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

            match = re.match(r_pattern, file_path.name)

            if not match:
                raise ValueError(f"Invalid file name format: {file_path}")

            if len(r_groups) != len(match.groups()):
                raise ValueError(
                    "File regex config generated mismatched groups."
                    + f"\nFile name: {file_path.name}, regex: {r_pattern}, groups: {r_groups}"
                    ""
                )

            for i in range(len(match.groups())):
                file_dict[r_groups[i]] = match.group(i + 1)

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

        # Apply version-based folder naming before returning
        self._apply_version_based_folder_naming(all_available_files)

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
