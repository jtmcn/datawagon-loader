from typing import Dict, List

from datawagon.objects.managed_file_metadata import ManagedFileMetadata


class FileUtils(object):
    def group_by_base_name(
        self,
        file_info_list: List[ManagedFileMetadata],
    ) -> Dict[str, List[ManagedFileMetadata]]:
        grouped_files = {}
        for file_info in file_info_list:
            if file_info.base_name not in grouped_files:
                grouped_files[file_info.base_name] = [file_info]
            else:
                grouped_files[file_info.base_name].append(file_info)
        return grouped_files

    def check_for_duplicate_files(
        self, file_info_list: List[ManagedFileMetadata]
    ) -> List[ManagedFileMetadata]:
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
        self, file_info_list: List[ManagedFileMetadata]
    ) -> List[List[ManagedFileMetadata]]:
        grouped_files = self.group_by_base_name(file_info_list)
        different_file_versions = []

        for _, file_infos in grouped_files.items():
            file_versions = {file_info.file_version for file_info in file_infos}
            if len(file_versions) > 1:
                different_file_versions.append(file_infos)

        return different_file_versions

    def remove_file_extension(self, file_name: str) -> str:
        file_name_without_extension = None
        if file_name.endswith(".csv"):
            file_name_without_extension = file_name[:-4]
        elif file_name.endswith(".csv.gz"):
            file_name_without_extension = file_name[:-7]
        elif file_name.endswith(".csv.zip"):
            file_name_without_extension = file_name[:-8]
        elif file_name.endswith(".gz"):
            file_name_without_extension = file_name[:-3]
        elif file_name.endswith(".zip"):
            file_name_without_extension = file_name[:-4]
        else:
            raise ValueError(f"Invalid file name format: {file_name}")

        return file_name_without_extension
