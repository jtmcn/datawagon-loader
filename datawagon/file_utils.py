from typing import List, Dict
from pathlib import Path

from csv_file_info import CsvFileInfo


class FileUtils:
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

    def check_for_duplicate_files(self, file_info_list: List[CsvFileInfo]) -> List[CsvFileInfo]:
        file_names = [file_info.file_name for file_info in file_info_list]
        duplicate_file_names = set(
            [file_name for file_name in file_names if file_names.count(file_name) > 1]
        )
        duplicate_files = [file_info for file_info in file_info_list if file_info.file_name in duplicate_file_names]
        return duplicate_files


    def scan_for_csv_files(self, source_path: Path) -> List[Path]:
        return list(source_path.glob("**/*.csv.gz")) + list(source_path.glob("**/*.csv.zip"))

    def check_for_different_file_versions(self, file_info_list: List[CsvFileInfo]) -> List[List[CsvFileInfo]]:
        grouped_files = self.group_by_table_name(file_info_list)
        different_file_versions = []

        for table_name, file_infos in grouped_files.items():
            file_versions = {file_info.file_version for file_info in file_infos}
            if len(file_versions) > 1:
                different_file_versions.append(file_infos)

        return different_file_versions

# def list_to_dict(file_info_list: List[CsvFileInfo]) -> Dict[str, List]:
#     result = {}
#     for file_info in file_info_list:
#         for key, value in file_info.__dict__.items():
#             if key not in result:
#                 result[key] = [value]
#             else:
#                 result[key].append(value)
#     return result


# def file_info_df_from_path(input_path: Path):
#     input_files = file_scanner(input_path, ".csv.gz")

#     list_of_file_info = [
#         CsvFileInfo.build_data_item(input_file) for input_file in input_files
#     ]

#     file_info = list_to_dict(list_of_file_info)

#     return pd.DataFrame(file_info)
