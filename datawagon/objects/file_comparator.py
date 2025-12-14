"""File comparison utilities for local vs bucket files.

This module provides the FileComparator class for comparing files in the local
source directory against files in the GCS bucket to identify new files that
need to be uploaded.
"""

from typing import List

import pandas as pd

from datawagon.objects.current_table_data import CurrentDestinationData
from datawagon.objects.file_utils import FileUtils
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import ManagedFilesToDatabase


class FileComparator:
    """Handles comparison between local files and bucket files.

    Provides methods to compare files in the local source directory with files
    already in the GCS bucket, and to filter out files that have already been
    uploaded.

    Attributes:
        file_utils: FileUtils instance for grouping files by base name
    """

    def __init__(self) -> None:
        """Initialize FileComparator with FileUtils instance."""
        self.file_utils = FileUtils()

    def compare_files(
        self,
        local_files: List[ManagedFileMetadata],
        bucket_files: List[CurrentDestinationData],
    ) -> pd.DataFrame:
        """Create DataFrame comparing local files to bucket files.

        Compares the count of files in the local source directory against
        the count of files already in the GCS bucket, grouped by base name.

        Args:
            local_files: Files in local source directory
            bucket_files: Files currently in GCS bucket

        Returns:
            DataFrame with columns: Base Name, DB File Count, Source File Count
            Sorted by Base Name in ascending order

        Example:
            >>> comparator = FileComparator()
            >>> local_files = [...]  # List of ManagedFileMetadata
            >>> bucket_files = [...]  # List of CurrentDestinationData
            >>> df = comparator.compare_files(local_files, bucket_files)
            >>> print(df)
            Base Name         DB File Count  Source File Count
            claim_raw         10             12
            revenue_summary   5              5
        """
        grouped_files = self.file_utils.group_by_base_name(local_files)

        bucket_file_dict = {table_data.base_name: table_data.file_count for table_data in bucket_files}

        all_base_names = set(grouped_files.keys()).union(bucket_file_dict.keys())

        data_rows = []

        for base_name in all_base_names:
            source_file_count = len(grouped_files.get(base_name, []))
            db_file_count = bucket_file_dict.get(base_name, 0)

            data_rows.append(
                {
                    "Base Name": base_name,
                    "DB File Count": db_file_count,
                    "Source File Count": source_file_count,
                }
            )

        display_table_data = pd.DataFrame(data_rows)

        return display_table_data.sort_values(by=["Base Name"])

    def find_new_files(
        self,
        all_local_files: List[ManagedFilesToDatabase],
        bucket_files: List[CurrentDestinationData],
    ) -> List[ManagedFilesToDatabase]:
        """Filter local files to only those not yet in bucket.

        Compares local source files against files already in the destination bucket
        and returns only the new files that haven't been uploaded yet.

        Args:
            all_local_files: All local files grouped by table
            bucket_files: Files currently in bucket

        Returns:
            List of file groups containing only new files
            Each group's files list is filtered to exclude already-uploaded files
            and sorted by base_name

        Example:
            >>> comparator = FileComparator()
            >>> local_groups = [...]  # List of ManagedFilesToDatabase
            >>> bucket_files = [...]  # List of CurrentDestinationData
            >>> new_groups = comparator.find_new_files(local_groups, bucket_files)
            >>> new_file_count = sum(len(group.files) for group in new_groups)
            >>> print(f"Found {new_file_count} new files")
        """
        existing_files: set[str] = set(
            [
                source_file
                for current_database_file in bucket_files
                for source_file in current_database_file.source_files
            ]
        )

        for range_index in range(len(all_local_files)):
            all_local_files[range_index].files = sorted(
                [file for file in all_local_files[range_index].files if (file.file_name not in existing_files)],
                key=lambda x: x.base_name,
            )

        return all_local_files
