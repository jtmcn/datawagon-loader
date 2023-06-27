import csv
from datetime import datetime, timezone
import gzip
from io import TextIOWrapper
import zipfile
import pandas as pd
from typing import Any, List, Tuple
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

        return self._create_dataframe(data, header)

    def _load_csv(self) -> Tuple[List[Any], List[str]]:
        with open(self.input_file.file_path, mode="rt", encoding="utf-8") as csv_file:
            csv_reader = csv.reader(csv_file)
            # Some files contain an invalid row above the header row
            # it can be identified if it contains only one column
            header = next(csv_reader)
            if len(header) == 1:
                header = next(csv_reader)
            data = [row for row in csv_reader]

        return data, header

    def _load_gzipped_csv(self) -> Tuple[List[Any], List[str]]:
        with gzip.open(
            self.input_file.file_path, mode="rt", encoding="utf-8"
        ) as csv_file:
            csv_reader = csv.reader(csv_file)

            header = next(csv_reader)
            if len(header) == 1:
                header = next(csv_reader)
            data = [row for row in csv_reader]

            return data, header

    def _load_zipped_csv(self) -> Tuple[List[Any], List[str]]:
        with zipfile.ZipFile(self.input_file.file_path, "r") as zipped_file:
            with zipped_file.open(zipped_file.namelist()[0], "r") as csv_file:
                # convert bytes to strings
                csv_reader = csv.reader(TextIOWrapper(csv_file))

                header = next(csv_reader)
                if len(header) == 1:
                    header = next(csv_reader)
                data = [row for row in csv_reader]

        return data, header

    def _format_columns(self, columns: List[str]) -> List[str]:
        # Column headers are inconsistent do not make good table names,
        # so we format them to snake_case
        return [
            col.replace(" ", "_")
            .replace(":", "")
            .replace("(", "_")
            .replace(")", "")
            .lower()
            for col in columns
        ]

    def _append_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        # These columns are not present in the csv files and will be added to all tables
        df["_file_name"] = self.input_file.file_name_without_extension
        df["_content_owner"] = self.input_file.content_owner
        df["_file_date"] = self.input_file.file_date
        df["_month_end_date"] = self.input_file.month_end_date
        df["_month_end_date_key"] = self.input_file.month_end_date_key
        df["_file_load_date"] = datetime.now(timezone.utc)

        return df

    def _create_dataframe(self, data: List[Any], header: List[str]) -> pd.DataFrame:
        columns = self._format_columns(header)

        df_raw = pd.DataFrame(data, columns=columns)

        df_appended = self._append_columns(df_raw)

        datatype_dict = {}

        float_cols = ["revenue"]
        int_cols = ["view", "day", "date_key"]
        date_cols = ["date"]

        for col in df_appended.columns:
            if any(name in col for name in float_cols):
                datatype_dict[col] = "float"
            elif any(name in col for name in int_cols):
                datatype_dict[col] = "int"
            elif any(name in col for name in date_cols):
                datatype_dict[col] = "datetime64[ns]"
            else:
                datatype_dict[col] = "object"
        df = df_appended.astype(datatype_dict)

        return df
