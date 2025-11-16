import csv
import gzip
import zipfile
from datetime import datetime, timezone
from io import TextIOWrapper
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from datawagon.objects.data_type_config import DataProcessingConfig
from datawagon.objects.managed_file_metadata import ManagedFileMetadata


class CSVLoader:
    """Handles loading and processing of CSV files in various formats.

    Supports .csv, .csv.gz, and .csv.zip file formats.
    Automatically detects and handles invalid header rows.
    Applies consistent column formatting and adds metadata columns.
    """

    def __init__(
        self,
        input_file: ManagedFileMetadata,
        processing_config: Optional[DataProcessingConfig] = None,
    ) -> None:
        """Initialize the CSV loader with file metadata.

        Args:
            input_file: Metadata about the file to be loaded
            processing_config: Configuration for data processing, uses defaults if None
        """
        self.input_file = input_file
        self.processing_config = processing_config or DataProcessingConfig()

    def load_data(self) -> pd.DataFrame:
        """Load and process the CSV file into a pandas DataFrame.

        Returns:
            Processed DataFrame with cleaned column names and metadata

        Raises:
            ValueError: If the file extension is not supported
        """
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
        """Load data from a regular CSV file.

        Returns:
            Tuple of (data rows, header columns)
        """
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
        """Load data from a gzipped CSV file.

        Returns:
            Tuple of (data rows, header columns)
        """
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
        """Load data from a ZIP file containing a CSV.

        Assumes the ZIP file contains exactly one CSV file.

        Returns:
            Tuple of (data rows, header columns)
        """
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
        """Format column names using configured transformations.

        Args:
            columns: Original column names

        Returns:
            Formatted column names
        """
        formatted_columns = []
        for col in columns:
            formatted_col = col

            # Apply character replacements
            for (
                old_char,
                new_char,
            ) in self.processing_config.column_transforms.replacements.items():
                formatted_col = formatted_col.replace(old_char, new_char)

            # Apply lowercase if configured
            if self.processing_config.column_transforms.to_lowercase:
                formatted_col = formatted_col.lower()

            formatted_columns.append(formatted_col)

        return formatted_columns

    def _append_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add metadata columns to the DataFrame.

        Adds _file_name, _content_owner, _report_date_key, and _file_load_date.

        Args:
            df: Original DataFrame

        Returns:
            DataFrame with additional metadata columns
        """
        # These columns are not present in the csv files and will be added to all tables
        # if isinstance(self.input_file, CsvFileInfo):
        df["_file_name"] = self.input_file.file_name
        if self.input_file.content_owner:
            df["_content_owner"] = self.input_file.content_owner
        if self.input_file.report_date_key:
            df["_report_date_key"] = self.input_file.report_date_key

        df["_file_load_date"] = datetime.now(timezone.utc).replace(tzinfo=None)

        return df

    def _create_dataframe(self, data: List[Any], header: List[str]) -> pd.DataFrame:
        """Create a properly formatted DataFrame from raw data.

        Applies column formatting, adds metadata, and sets appropriate data types.

        Args:
            data: Raw data rows
            header: Column names

        Returns:
            Formatted DataFrame with proper data types
        """
        columns = self._format_columns(header)

        df_raw = pd.DataFrame(data, columns=columns)

        df_with_appended = self._append_columns(df_raw)

        datatype_dict = self._infer_column_types(df_with_appended.columns.tolist())
        df = df_with_appended.astype(datatype_dict)

        return df

    def _infer_column_types(self, columns: List[str]) -> Dict[str, str]:
        """Infer data types for columns based on configuration.

        Args:
            columns: List of column names

        Returns:
            Dictionary mapping column names to data types
        """
        datatype_dict = {}
        config = self.processing_config.column_types

        for col in columns:
            if any(pattern in col for pattern in config.float_patterns):
                datatype_dict[col] = "float64"
            elif any(pattern in col for pattern in config.int_patterns):
                datatype_dict[col] = "int"
            elif any(pattern in col for pattern in config.date_patterns):
                datatype_dict[col] = "datetime64[ns]"
            else:
                datatype_dict[col] = config.default_type

        return datatype_dict
