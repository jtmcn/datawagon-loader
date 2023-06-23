import csv
import gzip
from io import TextIOWrapper
import zipfile
import pandas as pd
from typing import List, Tuple
from datawagon.objects.csv_file_info import CsvFileInfo


class CSVLoader(object):
    def __init__(self, input_file: CsvFileInfo) -> None:
        self.input_file = input_file

    def load_data(self) -> pd.DataFrame:
        file_extension = self.input_file.file_path.suffix.lower()

        if file_extension == ".gz":
            data, header = self._load_gzipped_csv()
        elif file_extension == ".zip":
            data, header = self._load_zipped_csv()
        elif file_extension == ".csv":
            data, header = self._load_csv()
        else:
            raise ValueError(
                f"Unsupported file extension: {file_extension}."
                + "Supported extensions are .csv, .csv.gz and .csv.zip"
            )

        columns = [
            col.replace(" ", "_")
            .replace(":", "")
            .replace("(", "_")
            .replace(")", "")
            .lower()
            for col in header
        ]

        df = pd.DataFrame(data, columns=columns)

        df["file_name"] = self.input_file.file_name_without_extension
        df["content_owner"] = self.input_file.content_owner

        return df

    def _load_csv(self) -> Tuple[List[List[str]], List[str]]:
        with open(self.input_file.file_path, mode="rt", encoding="utf-8") as csv_file:
            csv_reader = csv.reader(csv_file)
            # Some files contain an invalid row above the header row
            header = next(csv_reader)
            if len(header) == 1:
                header = next(csv_reader)
            data = [row for row in csv_reader]

        return data, header

    def _load_gzipped_csv(self) -> Tuple[List[List[str]], List[str]]:
        with gzip.open(
            self.input_file.file_path, mode="rt", encoding="utf-8"
        ) as csv_file:
            csv_reader = csv.reader(csv_file)

            header = next(csv_reader)
            if len(header) == 1:
                header = next(csv_reader)
            data = [row for row in csv_reader]

        return data, header

    def _load_zipped_csv(self) -> Tuple[List[List[str]], List[str]]:
        with zipfile.ZipFile(self.input_file.file_path, "r") as zipped_file:
            with zipped_file.open(zipped_file.namelist()[0], "r") as csv_file:
                # convert bytes to strings
                csv_reader = csv.reader(TextIOWrapper(csv_file))

                header = next(csv_reader)
                if len(header) == 1:
                    header = next(csv_reader)
                data = [row for row in csv_reader]

        return data, header
