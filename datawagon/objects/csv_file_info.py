import calendar
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class CsvFileInfo:
    """Class for properties used to upload .csv files into database"""

    file_path: Path
    file_dir: str
    file_name: str
    file_name_without_extension: str
    content_owner: str
    file_date_key: int
    file_date: date
    file_month_end_date: date
    file_month_end_date_key: int
    file_version: str
    table_name: str
    file_size_in_bytes: int
    file_size: str

    @classmethod
    def build_data_item(cls, input_file: Path) -> "CsvFileInfo":
        file_path = input_file

        file_size_in_bytes = file_path.stat().st_size
        file_size = cls.human_readable_size(file_size_in_bytes)

        file_dir = str(input_file.parent)

        file_name = input_file.name

        if input_file.suffix == ".csv":
            file_name_without_extension = re.sub(r"\.csv$", "", file_name)
        elif input_file.suffix == ".gz":
            file_name_without_extension = re.sub(r"\.csv(\.gz)?$", "", file_name)
        elif input_file.suffix == ".zip":
            file_name_without_extension = re.sub(r"\.csv(\.zip)?$", "", file_name)
        else:
            raise ValueError(f"Invalid file name format: {file_name}")

        # This pattern matches all monthtly YouTube files with dates in formats: YYYYMMDD or YYYYMM
        pattern = r"YouTube_(.+)_M_(\d{8}|\d{6})"
        match = re.search(pattern, file_name)
        if match:
            content_owner = match.group(1)
            file_date_key = int(match.group(2))
        else:
            raise ValueError(f"Invalid file name format: {input_file}")

        file_name_without_date_and_brand = re.sub(
            pattern + r"_", "", file_name_without_extension
        )

        # Check if the second date_key exists and remove it
        second_date_pattern = r"\d{8}_"
        file_name_without_second_date = re.sub(
            second_date_pattern, "", file_name_without_date_and_brand
        )

        file_version = cls.get_file_version(file_name)

        table_name = (
            re.sub(file_version, "", file_name_without_second_date)
            .replace("-", "_")
            .lower()
            .rstrip("_")
        )

        file_date = cls.date_key_to_date(file_date_key)

        file_month_end_date = file_date.replace(
            day=calendar.monthrange(file_date.year, file_date.month)[1]
        )
        file_month_end_date_key = int(file_month_end_date.strftime("%Y%m%d"))

        if (
            file_name_without_extension is None
            or file_name_without_extension == ""
            or content_owner is None
            or content_owner == ""
            or table_name is None
            or table_name == ""
        ):
            raise ValueError(f"Invalid file name format: {input_file}")

        data_item = cls(
            file_path=file_path,
            file_dir=file_dir,
            file_name=file_name,
            file_name_without_extension=file_name_without_extension,
            content_owner=content_owner,
            file_date_key=file_date_key,
            file_date=file_date,
            file_version=file_version,
            table_name=table_name,
            file_size_in_bytes=file_size_in_bytes,
            file_size=file_size,
            file_month_end_date=file_month_end_date,
            file_month_end_date_key=file_month_end_date_key,
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

        # Extract year, month, and day as integers
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
