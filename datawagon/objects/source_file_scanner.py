import fnmatch
import os
import re
from pathlib import Path
from typing import List

import toml
from pydantic import BaseModel, Field, ValidationError

from datawagon.objects.app_config import AppConfig
from datawagon.objects.csv_file_info_override import CsvFileInfoOverride
from datawagon.objects.source_config import Source, SourceConfig, SourceFileAttributes


class SourceFiles(BaseModel):
    files: List[CsvFileInfoOverride] = Field(default_factory=list)
    file_selector: str


class SourceFilesToDatabase(SourceFiles):
    table_name: str
    # destination_table: str
    append_or_replace: str


class SourceFileScanner(object):
    def __init__(self, app_config: AppConfig) -> None:
        self.app_config = app_config

        try:
            source_config_file = toml.load(app_config.csv_source_config)
            self.valid_config = SourceConfig(**source_config_file)

        except ValidationError as e:
            raise ValueError(f"Validation Failed for source_config.toml\n{e}")

    def scan_for_csv_files_with_name(
        self, source_path: Path, glob_pat: str, exclude_pattern: str | None
    ) -> List[Path]:
        all_csv_files = self.find_files(source_path, glob_pat, exclude_pattern)
        # print(all_csv_files)
        # all_csv_files = list(source_path.glob(f"**/*{glob_pat}*.csv*"))
        # all_csv_files = list(source_path.glob(self.case_insensitive_glob(glob_pat)))
        # all_csv_files = self.find_files(
        #     source_path=source_path, glob_pat=glob_pat, ignore_case=True
        # )
        # exclude open files
        all_csv_files = [
            file for file in all_csv_files if not file.name.startswith(".~lock")
        ]
        file_names = [str(file) for file in all_csv_files]

        return [Path(file) for file in file_names]

    def find_files(
        self, base_path: Path, match_pattern: str, exclude_pattern: str | None
    ) -> List[Path]:
        matches = []

        match_pattern = match_pattern.lower()

        for root, dirnames, filenames in os.walk(base_path):
            for filename in filenames:
                if fnmatch.fnmatch(filename.lower(), f"*{match_pattern}*"):
                    if not fnmatch.fnmatch(filename.lower(), f"*{exclude_pattern}*"):
                        if not filename.startswith(".~lock"):
                            matches.append(
                                os.path.abspath(os.path.join(root, filename))
                            )

        print(matches)
        return [Path(match) for match in matches]

    def source_file_attrs(
        self,
        file_path: Path,
        file_source: Source,
        is_replace_override: bool = False,
    ) -> SourceFileAttributes:
        append_or_replace = (
            "replace" if is_replace_override else file_source.append_or_replace
        )

        file_dict = {
            "file_name": file_path.name,
            "file_path": file_path,
            "destination_table": file_source.destination_table,
            "append_or_replace": append_or_replace,
        }

        if file_source.regex_pattern and file_source.regex_group_names:
            r_pattern = file_source.regex_pattern
            r_groups = file_source.regex_group_names

            match = re.match(r_pattern, file_path.name)

            if not match:
                raise ValueError(f"Invalid file name format: {file_path.name}")

            if len(r_groups) != len(match.groups()):
                raise ValueError(
                    "File regex config generated mismatched groups."
                    + f"\nFile name: {file_path.name}, regex: {r_pattern}, groups: {r_groups}"
                    ""
                )

            for i in range(len(match.groups())):
                file_dict[r_groups[i]] = match.group(i + 1)

        return SourceFileAttributes(**file_dict)

    def matched_files(self) -> List[SourceFilesToDatabase]:
        all_available_files: List[SourceFilesToDatabase] = []

        valid_config = self.valid_config

        for file_id in valid_config.source:
            file_source = valid_config.source[file_id]
            if file_source.is_enabled:
                file_list = self.scan_for_csv_files_with_name(
                    self.app_config.csv_source_dir,
                    file_source.file_name_base,
                    file_source.exclude_file_name_base,
                )

                table_mapper = SourceFilesToDatabase(
                    table_name=file_source.destination_table,
                    append_or_replace=file_source.append_or_replace,
                    file_selector=file_source.file_name_base,
                )

                for file_path in file_list:
                    source_file = self.source_file_attrs(file_path, file_source)
                    source_file_info = CsvFileInfoOverride.build_data_item(source_file)
                    table_mapper.files.append(source_file_info)

                all_available_files.append(table_mapper)

        return all_available_files

    def matched_file(
        self,
        source_file_path: Path,
        input_file_base_name: str,
        is_replace_override: bool,
    ) -> SourceFilesToDatabase | None:
        valid_config = self.valid_config

        for file_id in valid_config.source:
            file_source = valid_config.source[file_id]
            if file_source.file_name_base == input_file_base_name:
                file_attrs = self.source_file_attrs(
                    source_file_path, file_source, is_replace_override
                )

                table_mapper = SourceFilesToDatabase(
                    table_name=file_source.destination_table,
                    append_or_replace=file_source.append_or_replace,
                    file_selector=file_source.file_name_base,
                    files=[CsvFileInfoOverride.build_data_item(file_attrs)],
                )
                return table_mapper

        return None
