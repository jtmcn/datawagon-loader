import csv
import gzip
import zipfile
from datetime import datetime, timezone
from io import TextIOWrapper
from typing import Any, List, Tuple

import pandas as pd

from datawagon.objects.managed_file_metadata import ManagedFileMetadata


class CSVLoader(object):
    def __init__(self, input_file: ManagedFileMetadata) -> None:
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
        # Column headers are inconsistent do not make good names in the database,
        # format them to snake_case
        return [
            col.replace(" ", "_")
            .replace(".", "_")
            .replace("-", "_")
            .replace("/", "_")
            .replace("(", "_")
            .replace(")", "")
            .replace("?", "")
            .replace(":", "")
            .lower()
            for col in columns
        ]

    def _append_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        # These columns are not present in the csv files and will be added to all tables
        # if isinstance(self.input_file, CsvFileInfo):
        df["_file_name"] = self.input_file.file_name_without_extension
        if self.input_file.content_owner:
            df["_content_owner"] = self.input_file.content_owner
        if self.input_file.report_date_key:
            df["_report_date_key"] = self.input_file.report_date_key

        df["_file_load_date"] = datetime.now(timezone.utc).replace(tzinfo=None)

        return df

    def _create_dataframe(self, data: List[Any], header: List[str]) -> pd.DataFrame:
        columns = self._format_columns(header)

        df_raw = pd.DataFrame(data, columns=columns)

        df_with_appended = self._append_columns(df_raw)

        datatype_dict = {}

        # TODO: move column overrides to source_config

        float_cols = ["revenue"]
        int_cols = ["view", "day", "date_key", "sec"]
        date_cols = ["date"]

        for col in df_with_appended.columns:
            if any(name in col for name in float_cols):
                # floats will be changed to numeric on load (pandas doesn't support the type)
                datatype_dict[col] = "float64"
            elif any(name in col for name in int_cols):
                datatype_dict[col] = "int"
            elif any(name in col for name in date_cols):
                datatype_dict[col] = "datetime64[ns]"
            else:
                datatype_dict[col] = "object"
        df = df_with_appended.astype(datatype_dict)

        return df
