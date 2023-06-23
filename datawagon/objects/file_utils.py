from typing import List, Dict
from pathlib import Path

from objects.csv_file_info import CsvFileInfo


class FileUtils(object):
    def group_by_table_name(
        self,
        file_info_list: List[CsvFileInfo],
    ) -> Dict[str, List[CsvFileInfo]]:
        grouped_files = {}
        for file_info in file_info_list:
            if file_info.table_name not in grouped_files:
                grouped_files[file_info.table_name] = [file_info]
            else:
                grouped_files[file_info.table_name].append(file_info)
        return grouped_files

    def check_for_duplicate_files(
        self, file_info_list: List[CsvFileInfo]
    ) -> List[CsvFileInfo]:
        file_names = [
            file_info.file_name_without_extension for file_info in file_info_list
        ]
        duplicate_file_names = set(
            [file_name for file_name in file_names if file_names.count(file_name) > 1]
        )
        duplicate_files = [
            file_info
            for file_info in file_info_list
            if file_info.file_name_without_extension in duplicate_file_names
        ]
        return duplicate_files

    def scan_for_csv_files(self, source_path: Path) -> List[Path]:
        all_csv_files = list(source_path.glob("**/*.csv*"))
        return self._filter_csv_files(all_csv_files)

    def _filter_csv_files(self, csv_files: List[Path]) -> List[Path]:
        included = ["video_summary"]
        excluded = ["summary"]

        filtered_csv_files = [
            csv_file
            for csv_file in csv_files
            if any(file_part in csv_file.name.lower() for file_part in included)
            or all(file_part not in csv_file.name.lower() for file_part in excluded)
        ]
        filtered_csv_files = [
            csv_file for csv_file in csv_files if "summary" not in csv_file.name.lower()
        ]
        return filtered_csv_files

    def check_for_different_file_versions(
        self, file_info_list: List[CsvFileInfo]
    ) -> List[List[CsvFileInfo]]:
        grouped_files = self.group_by_table_name(file_info_list)
        different_file_versions = []

        for table_name, file_infos in grouped_files.items():
            file_versions = {file_info.file_version for file_info in file_infos}
            if len(file_versions) > 1:
                different_file_versions.append(file_infos)

        return different_file_versions