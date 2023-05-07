import re
from dataclasses import dataclass
from pathlib import Path
from datetime import date


@dataclass
class CsvFileInfo:
    """Class for properties used to upload .csv files into database"""

    file_path: Path
    file_dir: str
    file_name: str
    brand_name: str
    file_date_key: int
    file_date: date
    file_version: str
    table_name: str
    # file_size_in_bytes: int
    # file_size: str

    @classmethod
    def build_data_item(cls, input_file: Path) -> "CsvFileInfo":
        file_path = input_file

        # file_size_in_bytes = file_path.stat().st_size
        # file_size = human_readable_size(file_size_in_bytes)

        file_dir = str(input_file.parent)

        file_name = input_file.name

        pattern = r"YouTube_(.+)_M_(\d{8})"
        match = re.search(pattern, file_name)
        if match:
            brand_name = match.group(1)
            file_date_key = int(match.group(2))
        else:
            raise ValueError(f"Invalid file name format: {file_name}")

        file_name_without_date_and_brand = re.sub(pattern + r"_", "", file_name)

        if input_file.suffix == ".gz":
            file_name_without_extension = re.sub(
                r"\.csv(\.gz)?$", "", file_name_without_date_and_brand
            )
        elif input_file.suffix == ".zip":
            file_name_without_extension = re.sub(
                r"\.csv(\.zip)?$", "", file_name_without_date_and_brand
            )
        else:
            raise ValueError(f"Invalid file name format: {file_name}")

        # Check if the second date_key exists and remove it
        second_date_pattern = r"\d{8}_"
        file_name_without_second_date = re.sub(
            second_date_pattern, "", file_name_without_extension
        )

        file_version = cls.get_file_version(file_name)

        table_name = re.sub(file_version, "", file_name_without_second_date).replace("-", "_").lower().rstrip("_")

        file_date = cls.date_key_to_date(file_date_key)

        data_item = cls(
            file_path=file_path,
            file_dir=file_dir,
            file_name=file_name,
            brand_name=brand_name,
            file_date_key=file_date_key,
            file_date=file_date,
            file_version=file_version,
            table_name=table_name,
            # file_size_in_bytes,
            # file_size,
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
        day = int(date_string[6:])

        # Create a datetime.date object
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