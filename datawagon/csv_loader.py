import csv
import gzip
from io import TextIOWrapper
import zipfile
from pathlib import Path
from typing import List, Tuple


class CSVLoader:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def load_data(self) -> Tuple[List[List[str]], List[str]]:
        file_extension = self.file_path.suffix.lower()

        if file_extension == ".gz":
            return self._load_gzipped_csv()
        elif file_extension == ".zip":
            return self._load_zipped_csv()
        else:
            raise ValueError("Unsupported file extension. Supported extensions are .gz and .zip")

    def _load_gzipped_csv(self) -> Tuple[List[List[str]], List[str]]:
        with gzip.open(self.file_path, mode="rt", encoding="utf-8") as file:
            reader = csv.reader(file)
            header = next(reader)
            data = [row for row in reader]
        return data, header

    def _load_zipped_csv(self) -> Tuple[List[List[str]], List[str]]:
        with zipfile.ZipFile(self.file_path, "r") as zipped_file:
            with zipped_file.open(zipped_file.namelist()[0], "rt") as csv_file:
                # TextIOWrapper used to convert bytes to strings
                csv_reader = csv.reader(TextIOWrapper(csv_file))
                header = next(csv_reader)
                data = [row for row in csv_reader]
        return data, header
