from typing import Dict, List

from datawagon.objects.source_file_metadata import SourceFileMetadata


class FileUtils(object):
    def group_by_table_name(
        self,
        file_info_list: List[SourceFileMetadata],
    ) -> Dict[str, List[SourceFileMetadata]]:
        grouped_files = {}
        for file_info in file_info_list:
            if file_info.table_name not in grouped_files:
                grouped_files[file_info.table_name] = [file_info]
            else:
                grouped_files[file_info.table_name].append(file_info)
        return grouped_files

    def check_for_duplicate_files(
        self, file_info_list: List[SourceFileMetadata]
    ) -> List[SourceFileMetadata]:
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

    def check_for_different_file_versions(
        self, file_info_list: List[SourceFileMetadata]
    ) -> List[List[SourceFileMetadata]]:
        grouped_files = self.group_by_table_name(file_info_list)
        different_file_versions = []

        for table_name, file_infos in grouped_files.items():
            file_versions = {file_info.file_version for file_info in file_infos}
            if len(file_versions) > 1:
                different_file_versions.append(file_infos)

        return different_file_versions
