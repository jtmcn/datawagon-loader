from pathlib import Path
from typing import Dict, List

from datawagon.objects.csv_file_info import CsvFileInfo


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
        file_names = [str(file) for file in all_csv_files]
        results = self._filter_csv_files(file_names)
        return [Path(file) for file in results]

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

    def _filter_csv_files(self, csv_files: List[str]) -> List[str]:
        included = ["video_summary"]
        excluded = ["summary", "backup"]

        filtered_csv_files = [
            csv_file
            for csv_file in csv_files
            if any(file_part in csv_file.lower() for file_part in included)
            or all(file_part not in csv_file.lower() for file_part in excluded)
        ]

        return filtered_csv_files
