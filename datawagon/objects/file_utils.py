import gzip
import io
import os
import zipfile
from pathlib import Path
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

        else:
            raise ValueError(f"Invalid file name format: {file_name}")

        return file_name_without_extension

    def csv_zip_to_gzip(
        self, input_zip_path: Path, remove_original_zip: bool = False
    ) -> str | None:
        """Convert a ZIP file containing CSV files to a GZIP file containing GZIP compressed CSV files
        Remove any directory structure from the ZIP file"""
        current_dir = os.path.dirname(input_zip_path)
        with zipfile.ZipFile(input_zip_path, "r") as input_zip:
            # Create a new output ZIP file in memory
            with io.BytesIO() as output_zip_buffer:
                with zipfile.ZipFile(
                    output_zip_buffer, "w", zipfile.ZIP_DEFLATED, allowZip64=True
                ) as output_zip:
                    # Iterate through the files in the input ZIP
                    output_gzip_path = None
                    for file_info in input_zip.infolist():
                        # Remove the path prefix from the filename
                        filename = os.path.basename(file_info.filename)
                        output_gzip_path = f"{current_dir}/{filename}.gz"
                        with input_zip.open(file_info.filename) as input_file:
                            if file_info.filename.lower().endswith(".csv"):
                                # Create a GZIP compressed file in memory
                                with io.BytesIO() as gzip_buffer:
                                    with gzip.GzipFile(
                                        fileobj=gzip_buffer, mode="w"
                                    ) as gzip_file:
                                        gzip_file.write(input_file.read())
                                    gzip_buffer.seek(0)

                                    # Add the GZIP file to the output ZIP
                                    output_zip.writestr(filename, gzip_buffer.read())

                if output_gzip_path is not None:
                    # Save the output Gzip file to disk
                    with open(output_gzip_path, "wb") as output_file:
                        output_file.write(output_zip_buffer.getvalue())

        # Optionally, delete the original ZIP file
        if remove_original_zip:
            os.remove(input_zip_path)

        return output_gzip_path.replace(current_dir, "") if output_gzip_path else None
