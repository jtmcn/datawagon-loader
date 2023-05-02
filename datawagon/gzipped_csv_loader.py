import csv
import gzip
from pathlib import Path
from typing import List, Tuple


class GzippedCSVLoader:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def load_data(self) -> Tuple[List[List[str]], List[str]]:
        with gzip.open(self.file_path, mode="rt", encoding="utf-8") as file:
            reader = csv.reader(file)
            header = next(reader)
            data = [row for row in reader]

        return data, header
