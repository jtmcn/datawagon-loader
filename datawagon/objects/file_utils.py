"""File utility functions for CSV file processing.

This module provides utilities for grouping files, detecting duplicates,
checking file versions, and converting between compression formats (ZIP to GZIP).
Includes security validation for zip bombs.
"""
import gzip
import os
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List

from datawagon.logging_config import get_logger
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.security import SecurityError, check_zip_safety

logger = get_logger(__name__)


class FileUtils:
    """Utility class for file operations and validation.

    Provides methods for grouping files, detecting duplicates, checking versions,
    and converting between compression formats.
    """
    def group_by_base_name(
        self,
        file_info_list: List[ManagedFileMetadata],
    ) -> Dict[str, List[ManagedFileMetadata]]:
        """Group files by their base_name.

        Args:
            file_info_list: List of file metadata objects

        Returns:
            Dictionary mapping base_name to list of files with that base_name

        Example:
            >>> utils = FileUtils()
            >>> files = [file1, file2]  # Same base_name
            >>> grouped = utils.group_by_base_name(files)
            >>> grouped["YouTube_Brand_M"]
            [file1, file2]
        """
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
        """Find duplicate files based on file_name.

        Args:
            file_info_list: List of file metadata objects

        Returns:
            List of file metadata objects with duplicate file_name

        Example:
            >>> utils = FileUtils()
            >>> dupes = utils.check_for_duplicate_files(files)
            >>> len(dupes)
            2  # Two files with same name
        """
        file_names = [file_info.file_name for file_info in file_info_list]

        duplicate_files = []
        for file_info in file_info_list:
            if file_names.count(file_info.file_name) > 1:
                duplicate_files.append(file_info)

        return duplicate_files

    def check_for_different_file_versions(
        self, file_info_list: List[ManagedFileMetadata]
    ) -> List[List[ManagedFileMetadata]]:
        """Find groups of files with different versions.

        Groups files by base_name and identifies groups where multiple
        file_version values exist.

        Args:
            file_info_list: List of file metadata objects

        Returns:
            List of file groups with mixed versions

        Example:
            >>> utils = FileUtils()
            >>> mixed = utils.check_for_different_file_versions(files)
            >>> len(mixed[0])
            2  # Group with v1-0 and v1-1 versions
        """
        grouped_files = self.group_by_base_name(file_info_list)
        different_file_versions = []

        for _, file_infos in grouped_files.items():
            file_versions = {file_info.file_version for file_info in file_infos}
            if len(file_versions) > 1:
                different_file_versions.append(file_infos)

        return different_file_versions

    def csv_gzipped(
        self, input_csv_file: Path, remove_original_zip: bool = False
    ) -> Path:
        """Compress CSV file to GZIP format.

        Args:
            input_csv_file: Path to CSV file to compress
            remove_original_zip: Remove original CSV after compression

        Returns:
            Path to created .csv.gz file

        Example:
            >>> utils = FileUtils()
            >>> output = utils.csv_gzipped(Path("data.csv"), remove_original_zip=True)
            >>> output
            Path('data.csv.gz')
        """
        is_successful = False
        output_gzip_path = f"{input_csv_file}.gz"

        with open(input_csv_file, "rb") as f_in:
            with gzip.open(output_gzip_path, "wb") as f_out:
                try:
                    shutil.copyfileobj(f_in, f_out)
                    is_successful = True
                except Exception as e:
                    logger.error(f"Failed to gzip file: {e}")

        if remove_original_zip and is_successful:
            os.remove(input_csv_file)

        return Path(output_gzip_path)

    def csv_zip_to_gzip(
        self, input_zip_path: Path, remove_original_zip: bool = False
    ) -> Path:
        """Convert ZIP file containing CSV to GZIP format.

        Extracts CSV files from ZIP archive and converts to GZIP format,
        flattening any directory structure. Validates ZIP safety to prevent
        zip bombs before processing.

        Args:
            input_zip_path: Path to ZIP file containing CSV files
            remove_original_zip: Remove original ZIP after conversion

        Returns:
            Path to created .csv.gz file

        Raises:
            SecurityError: If ZIP file exceeds safety limits (zip bomb)

        Example:
            >>> utils = FileUtils()
            >>> output = utils.csv_zip_to_gzip(Path("data.zip"))
            >>> output
            Path('data.csv.gz')

        Note:
            Excludes __MACOSX metadata files automatically.
        """
        # Check zip safety before opening
        try:
            check_zip_safety(str(input_zip_path))
        except SecurityError as e:
            logger.error(f"Unsafe zip file: {e}")
            raise

        current_dir = os.path.dirname(input_zip_path)
        output_gzip_path = Path()
        is_successful = False
        with zipfile.ZipFile(input_zip_path, "r") as input_zip:
            for file_info in input_zip.infolist():
                if "__MACOSX" not in file_info.filename:
                    filename = os.path.basename(file_info.filename)
                    output_gzip_path = Path(f"{current_dir}/{filename}.gz")
                    with input_zip.open(file_info.filename) as input_file:
                        if file_info.filename.lower().endswith(".csv"):
                            with gzip.open(output_gzip_path, "wb") as gzip_file:
                                for chunk in iter(
                                    lambda: input_file.read(1024 * 1024), b""
                                ):  # 1MB chunks
                                    gzip_file.write(chunk)
                                is_successful = True

        if remove_original_zip and is_successful:
            os.remove(input_zip_path)

        return Path(output_gzip_path)
