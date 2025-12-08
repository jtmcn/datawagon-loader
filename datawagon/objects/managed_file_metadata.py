"""File metadata models for tracking CSV file properties.

This module defines Pydantic models for managing file metadata throughout the
processing pipeline. Includes utilities for file version extraction, date conversion,
and human-readable file size formatting.
"""
import calendar
import re
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel


class ManagedFileInput(BaseModel):
    """Input model for CSV file before metadata enrichment.

    Represents basic file attributes extracted from filesystem and configuration,
    before additional metadata (version, dates, sizes) is computed.

    Attributes:
        file_name: Name of the file with extension
        file_path: Full path to the file
        base_name: Base pattern matched (e.g., "YouTube_Brand_M")
        table_name: Destination table name
        table_append_or_replace: Upload strategy ("append" or "replace")
        storage_folder_name: GCS folder name for upload

    Note:
        Allows additional fields defined at runtime via regex_group_names
        (e.g., content_owner, file_date_key).

    Example:
        >>> file_input = ManagedFileInput(
        ...     file_name="YouTube_Brand_M_20230601.csv",
        ...     file_path=Path("/data/file.csv"),
        ...     base_name="YouTube_Brand_M",
        ...     table_name="youtube_raw",
        ...     table_append_or_replace="append",
        ...     storage_folder_name="youtube_analytics"
        ... )
    """

    # TODO: merge with SourceFileMetadata
    file_name: str
    file_path: Path
    base_name: str
    table_name: str
    table_append_or_replace: Literal["append", "replace"]
    storage_folder_name: str

    # allows for additional fields defined at runtime by regex_group_names
    class Config:
        extra = "allow"


class ManagedFileMetadata(ManagedFileInput):
    """Enriched metadata for CSV file ready for GCS upload.

    Extends ManagedFileInput with computed metadata including file version,
    file size, report dates, and content owner. This model represents the
    complete file context needed for partitioned GCS uploads.

    Attributes:
        file_dir: Directory path containing the file
        content_owner: Content owner extracted from filename (optional)
        report_date_key: Report date in YYYYMMDD format as integer (optional)
        report_date_str: Report date in YYYY-MM-DD format for partitioning (optional)
        file_version: Extracted version string (e.g., "v1-1") or empty string
        file_size_in_bytes: File size in bytes
        file_size: Human-readable file size (e.g., "2.50 MB")

    Note:
        Allows additional fields from regex extraction via Config.extra = "allow".
    """

    file_dir: str
    # file_name_without_extension: str
    content_owner: Optional[str]
    report_date_key: Optional[int]
    report_date_str: Optional[str]
    file_version: str
    file_size_in_bytes: int
    file_size: str

    class Config:
        extra = "allow"

    @classmethod
    def build_data_item(cls, source_file: ManagedFileInput) -> "ManagedFileMetadata":
        """Build enriched file metadata from basic file input.

        Computes file version, file size, report dates, and content owner from
        the source file input. Converts file_date_key (YYYYMMDD or YYYYMM) to
        month-end date for partitioning.

        Args:
            source_file: Basic file input with path and configuration

        Returns:
            Enriched ManagedFileMetadata with computed fields

        Example:
            >>> input_file = ManagedFileInput(...)
            >>> metadata = ManagedFileMetadata.build_data_item(input_file)
            >>> metadata.report_date_str
            '2023-06-30'
        """
        file_path = source_file.file_path

        file_size_in_bytes = file_path.stat().st_size
        file_size = cls.human_readable_size(file_size_in_bytes)

        file_dir = str(file_path.parent)

        file_name = file_path.name

        file_version = cls.get_file_version(file_name)

        file_attributes_dict = source_file.model_dump()

        report_date_key, report_date_str = None, None

        if "file_date_key" in file_attributes_dict.keys():
            file_date_key = file_attributes_dict["file_date_key"]

            file_date = cls.date_key_to_date(file_date_key)

            file_month_end_date = file_date.replace(
                day=calendar.monthrange(file_date.year, file_date.month)[1]
            )

            report_date_str = file_month_end_date.strftime("%Y-%m-%d")

            report_date_key = int(file_month_end_date.strftime("%Y%m%d"))

        content_owner = None

        if "content_owner" in file_attributes_dict.keys():
            content_owner = file_attributes_dict["content_owner"]

        # TODO: handle user defined props with *kwargs
        data_item = cls(
            file_path=file_path,
            file_dir=file_dir,
            file_name=file_name,
            # file_name_without_extension=file_name_without_extension,
            file_version=file_version,
            base_name=source_file.base_name,
            table_name=source_file.table_name,
            file_size_in_bytes=file_size_in_bytes,
            file_size=file_size,
            table_append_or_replace=source_file.table_append_or_replace,
            report_date_key=report_date_key,
            report_date_str=report_date_str,
            content_owner=content_owner,
            storage_folder_name=source_file.storage_folder_name
            or source_file.base_name,
        )

        return data_item

    @staticmethod
    def get_file_version(file_name: str) -> str:
        """Extract version string from filename.

        Searches for version pattern "_v{digits}" or "_v{digits}-{digits}"
        in filename and returns the version without leading underscore.

        Args:
            file_name: Filename to extract version from

        Returns:
            Version string (e.g., "v1", "v1-1") or empty string if no version found

        Example:
            >>> ManagedFileMetadata.get_file_version("data_v1-1.csv")
            'v1-1'
            >>> ManagedFileMetadata.get_file_version("data.csv")
            ''
        """
        file_version_pattern = r"_v\d+(-\d+)?"
        match = re.search(file_version_pattern, file_name)
        if match:
            return match.group(0).lstrip("_")  # Remove the leading underscore
        else:
            return ""

    @staticmethod
    def date_key_to_date(date_key: int) -> date:
        """Convert integer date key to date object with validation.

        Supports two formats:
        - YYYYMMDD (8 digits): Full date
        - YYYYMM (6 digits): Month (day defaults to 1)

        Args:
            date_key: Date in YYYYMMDD or YYYYMM format

        Returns:
            date object representing the date

        Raises:
            ValueError: If date_key is invalid format or represents invalid date

        Example:
            >>> ManagedFileMetadata.date_key_to_date(20230615)
            date(2023, 6, 15)
            >>> ManagedFileMetadata.date_key_to_date(202306)
            date(2023, 6, 1)
        """
        date_string = str(date_key)

        # Validate format
        if len(date_string) not in [6, 8]:
            raise ValueError(
                f"Invalid date_key format: {date_key}. "
                f"Expected YYYYMMDD (8 digits) or YYYYMM (6 digits), got {len(date_string)} digits"
            )

        try:
            year = int(date_string[:4])
            month = int(date_string[4:6])
            day = int(date_string[6:8]) if len(date_string) == 8 else 1

            # Validate ranges
            if not (1900 <= year <= 2100):
                raise ValueError(f"Year out of range: {year}")
            if not (1 <= month <= 12):
                raise ValueError(f"Invalid month: {month}")
            if not (1 <= day <= 31):
                raise ValueError(f"Invalid day: {day}")

            # Let date() constructor validate day for month
            return date(year, month, day)

        except ValueError as e:
            raise ValueError(
                f"Invalid date_key: {date_key} -> {date_string}. {str(e)}"
            ) from e

    @staticmethod
    def human_readable_size(size: int) -> str:
        """Convert file size in bytes to human-readable format.

        Converts byte size to appropriate unit (B, KB, MB, GB, TB, PB) with
        two decimal places.

        Args:
            size: File size in bytes

        Returns:
            Formatted size string with unit (e.g., "2.50 MB")

        Example:
            >>> ManagedFileMetadata.human_readable_size(2048)
            '2.00 KB'
            >>> ManagedFileMetadata.human_readable_size(5242880)
            '5.00 MB'
        """
        unit_list = ["B", "KB", "MB", "GB", "TB", "PB"]
        index = 0

        f_size = size.__float__()
        while f_size >= 1024.0 and index < len(unit_list) - 1:
            f_size /= 1024.0
            index += 1

        return f"{f_size:.2f} {unit_list[index]}"
