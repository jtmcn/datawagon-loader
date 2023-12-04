import calendar
import re
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel


class ManagedFileInput(BaseModel):
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
    """Class for properties used to upload .csv files into database"""

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
        file_path = source_file.file_path

        file_size_in_bytes = file_path.stat().st_size
        file_size = cls.human_readable_size(file_size_in_bytes)

        file_dir = str(file_path.parent)

        file_name = file_path.name

        # TODO: replace following with FileUtils.remove_file_extension
        # if file_path.suffix == ".csv":
        #     file_name_without_extension = re.sub(r"\.csv$", "", file_name)
        # elif file_path.suffix == ".gz":
        #     file_name_without_extension = re.sub(r"\.csv(\.gz)?$", "", file_name)
        # elif file_path.suffix == ".zip":
        #     file_name_without_extension = re.sub(r"\.csv(\.zip)?$", "", file_name)
        # else:
        #     raise ValueError(f"Invalid file name format: {file_name}")

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
        file_version_pattern = r"_v\d+(-\d+)?"
        match = re.search(file_version_pattern, file_name)
        if match:
            return match.group(0).lstrip("_")  # Remove the leading underscore
        else:
            return ""

    @staticmethod
    def date_key_to_date(date_key: int) -> date:
        date_string = str(date_key)

        year = int(date_string[:4])
        month = int(date_string[4:6])
        day = int(date_string[6:]) if len(date_string) > 6 else 1

        return date(year, month, day)

    @staticmethod
    def human_readable_size(size: int) -> str:
        unit_list = ["B", "KB", "MB", "GB", "TB", "PB"]
        index = 0

        f_size = size.__float__()
        while f_size >= 1024.0 and index < len(unit_list) - 1:
            f_size /= 1024.0
            index += 1

        return f"{f_size:.2f} {unit_list[index]}"
