"""BigQuery schema inference from GCS CSV files.

This module provides utilities to infer BigQuery schemas from CSV files in GCS,
with column name normalization to lowercase and special character handling.
"""

import csv
import gzip
import re
import time
from io import BytesIO
from typing import List, Optional, Tuple

from google.api_core import exceptions as google_api_exceptions
from google.cloud import bigquery, storage

from datawagon.bucket.retry_utils import retry_with_backoff
from datawagon.logging_config import get_logger

logger = get_logger(__name__)

# GCS transient failures that should be retried
TRANSIENT_EXCEPTIONS = (
    google_api_exceptions.ServiceUnavailable,  # 503
    google_api_exceptions.DeadlineExceeded,  # 504
    google_api_exceptions.InternalServerError,  # 500
    google_api_exceptions.TooManyRequests,  # 429 rate limiting
)


class SchemaInferenceManager:
    """Infer BigQuery schemas from CSV files in GCS.

    Extracts CSV headers from GCS files and converts them to BigQuery
    SchemaField objects with normalized lowercase column names.

    Attributes:
        storage_client: GCS storage client
        bucket_name: GCS bucket name
    """

    # Default type inference settings
    DEFAULT_SAMPLE_SIZE = 100
    DEFAULT_CONFIDENCE_THRESHOLD = 0.95
    DEFAULT_MIN_NON_NULL_SAMPLES = 10

    # Type detection limits
    INT64_MIN = -(2**63)
    INT64_MAX = 2**63 - 1

    def __init__(self, storage_client: storage.Client, bucket_name: str) -> None:
        """Initialize schema inference manager.

        Args:
            storage_client: Authenticated GCS storage client
            bucket_name: GCS bucket containing CSV files
        """
        self.storage_client = storage_client
        self.bucket_name = bucket_name

    @staticmethod
    def normalize_column_names(columns: List[str]) -> List[str]:
        """Normalize column names to lowercase with underscores.

        Normalization rules:
        - Replaces special characters with underscores
        - Converts to lowercase
        - Handles duplicate names by appending _1, _2, etc.

        Args:
            columns: Raw column names from CSV header

        Returns:
            List of normalized column names

        Example:
            >>> SchemaInferenceManager.normalize_column_names(["Asset ID", "Revenue (USD)", "Date"])
            ['asset_id', 'revenue__usd_', 'date']
        """
        normalized = []
        for col in columns:
            # Normalize column names to BigQuery-compatible format
            normalized_col = (
                col.replace(" ", "_")
                .replace(".", "_")
                .replace("-", "_")
                .replace("/", "_")
                .replace("(", "_")
                .replace(")", "")
                .replace("?", "")
                .replace(":", "")
                .lower()
            )

            # Handle duplicates by appending suffix
            if normalized_col in normalized:
                suffix = 1
                while f"{normalized_col}_{suffix}" in normalized:
                    suffix += 1
                normalized_col = f"{normalized_col}_{suffix}"

            normalized.append(normalized_col)

        return normalized

    @staticmethod
    def _try_parse_bool(value: str) -> bool:
        """Check if value is a boolean.

        Accepts: true, false, TRUE, FALSE, yes, no, YES, NO, 1, 0

        Args:
            value: String value to check

        Returns:
            True if parseable as bool, False otherwise

        Example:
            >>> SchemaInferenceManager._try_parse_bool("true")
            True
            >>> SchemaInferenceManager._try_parse_bool("123")
            False
        """
        if not value:
            return False

        normalized = value.strip().lower()
        return normalized in {"true", "false", "yes", "no", "1", "0"}

    @staticmethod
    def _try_parse_int(value: str) -> bool:
        """Check if value is an integer.

        Rules:
        - Must parse cleanly as int
        - No leading zeros (except "0" itself) - "00123" is STRING
        - Must fit in INT64 range (-2^63 to 2^63-1)
        - No decimal points

        Args:
            value: String value to check

        Returns:
            True if valid INT64, False otherwise

        Example:
            >>> SchemaInferenceManager._try_parse_int("123")
            True
            >>> SchemaInferenceManager._try_parse_int("00123")
            False
        """
        if not value:
            return False

        try:
            # Check for leading zeros (except "0" or negative numbers)
            stripped = value.strip()
            if len(stripped) > 1 and stripped[0] == "0" and stripped[1].isdigit():
                return False  # "00123" -> STRING

            parsed = int(stripped)

            # Check INT64 range
            return SchemaInferenceManager.INT64_MIN <= parsed <= SchemaInferenceManager.INT64_MAX

        except (ValueError, OverflowError):
            return False

    @staticmethod
    def _try_parse_numeric(value: str) -> bool:
        """Check if value is numeric (integer or decimal).

        Accepts: "123", "123.45", "1e10", "1.0", ".5"
        Used for NUMERIC type (exact decimal precision)

        Args:
            value: String value to check

        Returns:
            True if parseable as numeric, False otherwise

        Example:
            >>> SchemaInferenceManager._try_parse_numeric("123.45")
            True
            >>> SchemaInferenceManager._try_parse_numeric("123")
            True
            >>> SchemaInferenceManager._try_parse_numeric("abc")
            False
        """
        if not value:
            return False

        try:
            float(value.strip())
            return True
        except (ValueError, OverflowError):
            return False

    @staticmethod
    def _try_parse_date(value: str) -> Optional[str]:
        """Detect date/timestamp format.

        Supported formats:
        - DATE: "YYYY-MM-DD", "YYYY/MM/DD"
        - TIMESTAMP: "YYYY-MM-DD HH:MM:SS", "YYYY-MM-DD HH:MM:SS.fff"

        Args:
            value: String value to check

        Returns:
            "DATE" or "TIMESTAMP" if parseable, None otherwise

        Example:
            >>> SchemaInferenceManager._try_parse_date("2023-06-30")
            'DATE'
            >>> SchemaInferenceManager._try_parse_date("2023-06-30 12:00:00")
            'TIMESTAMP'
        """
        if not value:
            return None

        stripped = value.strip()

        # Try timestamp first (more specific)
        timestamp_patterns = [
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$",  # YYYY-MM-DD HH:MM:SS.fff
            r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$",  # YYYY/MM/DD HH:MM:SS.fff
        ]

        for pattern in timestamp_patterns:
            if re.match(pattern, stripped):
                return "TIMESTAMP"

        # Try date patterns
        date_patterns = [
            r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
            r"^\d{4}/\d{2}/\d{2}$",  # YYYY/MM/DD
        ]

        for pattern in date_patterns:
            if re.match(pattern, stripped):
                return "DATE"

        return None

    @retry_with_backoff(retries=3, exceptions=TRANSIENT_EXCEPTIONS)
    def read_csv_header_and_sample(
        self, storage_folder_name: str, sample_size: int = 100
    ) -> Optional[Tuple[List[str], List[List[str]]]]:
        """Read CSV header and sample rows from first file in GCS folder.

        Finds the first .csv.gz file in the specified folder and extracts
        the header row plus sample_size data rows. Uses streaming to avoid
        downloading entire file.

        Args:
            storage_folder_name: GCS folder path (e.g., "caravan-versioned/claim_raw_v1-1")
            sample_size: Number of data rows to sample (default: 100)

        Returns:
            Tuple of (header, sample_rows) or None if no files found
            - header: List of column names from CSV header
            - sample_rows: List of rows, where each row is a list of values

        Raises:
            Exception: If blob download or decompression fails

        Example:
            >>> header, rows = manager.read_csv_header_and_sample("folder")
            >>> print(header)
            ['Asset ID', 'Revenue', 'Date']
            >>> print(len(rows))
            100
        """
        # List blobs in folder
        bucket = self.storage_client.bucket(self.bucket_name)
        blobs = list(bucket.list_blobs(prefix=storage_folder_name))

        # Find first .csv.gz file
        csv_blobs = [b for b in blobs if b.name.endswith(".csv.gz")]
        if not csv_blobs:
            logger.warning(f"No .csv.gz files found in {storage_folder_name}")
            return None

        first_blob = csv_blobs[0]
        logger.info(f"Reading header and {sample_size} rows from: {first_blob.name}")

        try:
            # Download blob to memory (not disk)
            blob_bytes = BytesIO()
            first_blob.download_to_file(blob_bytes)
            blob_bytes.seek(0)

            # Decompress gzip and read header + sample rows
            with gzip.open(blob_bytes, mode="rt", encoding="utf-8") as csv_file:
                csv_reader = csv.reader(csv_file)

                # Some files contain an invalid row above the header row
                # it can be identified if it contains only one column
                header = next(csv_reader)
                if len(header) == 1:
                    header = next(csv_reader)

                # Read sample rows
                sample_rows = []
                for i, row in enumerate(csv_reader):
                    if i >= sample_size:
                        break
                    sample_rows.append(row)

                logger.info(f"Sampled {len(sample_rows)} rows with {len(header)} columns")
                return (header, sample_rows)

        except gzip.BadGzipFile:
            logger.error(f"Failed to decompress {first_blob.name} - not a valid gzip file")
            return None
        except StopIteration:
            logger.error(f"Empty CSV file: {first_blob.name}")
            return None
        except Exception as e:
            logger.error(f"Error reading CSV header and sample: {e}", exc_info=True)
            return None

    def read_csv_header_from_gcs(self, storage_folder_name: str) -> Optional[List[str]]:
        """Read CSV header row from first file in GCS folder.

        Backward-compatible wrapper that returns only the header.

        Args:
            storage_folder_name: GCS folder path

        Returns:
            List of column names from CSV header, or None if no files found
        """
        result = self.read_csv_header_and_sample(storage_folder_name, sample_size=0)
        if result:
            return result[0]
        return None

    def infer_column_type(
        self,
        column_name: str,
        column_index: int,
        sample_rows: List[List[str]],
        confidence_threshold: float = 0.95,
        min_non_null_samples: int = 10,
    ) -> str:
        """Infer BigQuery type for a single column from sample data.

        Type detection order (most specific to least):
        1. INT64 - Whole numbers without decimals (checked before BOOL so "1"/"0" are numbers)
        2. BOOL - true/false/yes/no (excludes numeric "1"/"0")
        3. BIGNUMERIC - Numbers with decimals or scientific notation (exact precision, up to 38 decimal places)
        4. TIMESTAMP - YYYY-MM-DD HH:MM:SS format
        5. DATE - YYYY-MM-DD format
        6. STRING - Everything else (fallback)

        Special handling:
        - Columns containing "revenue" in name always prefer BIGNUMERIC over INT64
        - BIGNUMERIC accepts both integers and decimals (100, 100.50)
        - No FLOAT64 support (replaced with BIGNUMERIC for exact precision)

        Args:
            column_name: Column name (for logging)
            column_index: Column position in row
            sample_rows: List of data rows
            confidence_threshold: Minimum % of values matching type (default: 0.95)
            min_non_null_samples: Minimum non-null values required (default: 10)

        Returns:
            BigQuery type: "BOOL", "INT64", "BIGNUMERIC", "DATE", "TIMESTAMP", "STRING"

        Example:
            >>> manager.infer_column_type("partner_revenue", 1, sample_rows)
            'BIGNUMERIC'
        """
        # Extract non-null values for this column
        sample_values = []
        for row in sample_rows:
            # Handle rows with fewer columns than expected
            if column_index >= len(row):
                continue

            value = row[column_index].strip()
            # Skip empty/null values
            if value and value.lower() not in {"null", "none", ""}:
                sample_values.append(value)

        # Insufficient data -> STRING
        if len(sample_values) < min_non_null_samples:
            logger.warning(
                f"Column '{column_name}': Only {len(sample_values)} non-null samples, "
                f"using STRING (need {min_non_null_samples})"
            )
            return "STRING"

        # Count successful parses per type
        type_counts = {
            "BOOL": 0,
            "INT64": 0,
            "BIGNUMERIC": 0,
            "DATE": 0,
            "TIMESTAMP": 0,
            "STRING": len(sample_values),  # Everything can be STRING
        }

        for value in sample_values:
            # Try types in order (most specific first)
            # Check INT64 before BOOL so "1" and "0" are recognized as numbers
            if self._try_parse_int(value):
                type_counts["INT64"] += 1
            elif self._try_parse_bool(value):
                type_counts["BOOL"] += 1
            elif self._try_parse_numeric(value):
                type_counts["BIGNUMERIC"] += 1
            else:
                date_type = self._try_parse_date(value)
                if date_type == "TIMESTAMP":
                    type_counts["TIMESTAMP"] += 1
                elif date_type == "DATE":
                    type_counts["DATE"] += 1

        # Calculate confidence for each type
        total_samples = len(sample_values)

        # Special handling for revenue columns
        is_revenue_column = "revenue" in column_name.lower()

        if is_revenue_column:
            # Revenue columns: combine INT64 + BIGNUMERIC counts
            numeric_confidence = (type_counts["INT64"] + type_counts["BIGNUMERIC"]) / total_samples
            if numeric_confidence >= confidence_threshold:
                logger.info(
                    f"Column '{column_name}': Inferred BIGNUMERIC (revenue column) "
                    f"({type_counts['INT64']}+{type_counts['BIGNUMERIC']}/{total_samples} = {numeric_confidence:.1%})"
                )
                return "BIGNUMERIC"

        # Check types in priority order (matches detection order above)
        type_priority = ["INT64", "BOOL", "BIGNUMERIC", "TIMESTAMP", "DATE"]

        for bq_type in type_priority:
            confidence = type_counts[bq_type] / total_samples
            if confidence >= confidence_threshold:
                logger.info(
                    f"Column '{column_name}': Inferred {bq_type} "
                    f"({type_counts[bq_type]}/{total_samples} = {confidence:.1%})"
                )
                return bq_type

        # Fallback to STRING
        logger.info(f"Column '{column_name}': No type meets {confidence_threshold:.0%} threshold, using STRING")
        return "STRING"

    def infer_schema(self, storage_folder_name: str) -> Optional[List[bigquery.SchemaField]]:
        """Infer BigQuery schema from CSV files in GCS folder.

        Uses data-driven type inference by sampling 100 rows from CSV files
        and analyzing actual data values for each column.

        Args:
            storage_folder_name: GCS folder path

        Returns:
            List of BigQuery SchemaField objects with inferred types, or None if inference fails

        Example:
            >>> manager.infer_schema("caravan-versioned/claim_raw_v1-1")
            [
                SchemaField('asset_id', 'STRING', mode='NULLABLE'),
                SchemaField('partner_revenue', 'BIGNUMERIC', mode='NULLABLE'),
                SchemaField('views', 'INT64', mode='NULLABLE'),
                SchemaField('report_date', 'DATE', mode='NULLABLE'),
                ...
            ]
        """
        # Start timing
        start_time = time.perf_counter()

        # Read CSV header and sample rows for type inference
        result = self.read_csv_header_and_sample(storage_folder_name, sample_size=self.DEFAULT_SAMPLE_SIZE)

        if not result:
            duration = time.perf_counter() - start_time
            logger.error(f"Cannot infer schema after {duration:.2f}s: no data found in {storage_folder_name}")
            return None

        header, sample_rows = result

        # Normalize column names
        normalized_columns = self.normalize_column_names(header)

        if not normalized_columns:
            duration = time.perf_counter() - start_time
            logger.error(f"Cannot infer schema after {duration:.2f}s: no columns after normalization")
            return None

        # If no sample rows, fall back to all-STRING schema
        if not sample_rows:
            duration = time.perf_counter() - start_time
            logger.warning(
                f"No sample rows available, creating all-STRING schema for {len(normalized_columns)} columns "
                f"in {duration:.2f}s"
            )
            schema = [bigquery.SchemaField(col_name, "STRING", mode="NULLABLE") for col_name in normalized_columns]
            return schema

        # Infer type for each column from sample data
        schema = []
        type_distribution = {"BOOL": 0, "INT64": 0, "BIGNUMERIC": 0, "DATE": 0, "TIMESTAMP": 0, "STRING": 0}

        for i, col_name in enumerate(normalized_columns):
            inferred_type = self.infer_column_type(
                column_name=col_name,
                column_index=i,
                sample_rows=sample_rows,
                confidence_threshold=self.DEFAULT_CONFIDENCE_THRESHOLD,
                min_non_null_samples=self.DEFAULT_MIN_NON_NULL_SAMPLES,
            )

            schema.append(bigquery.SchemaField(col_name, inferred_type, mode="NULLABLE"))
            type_distribution[inferred_type] += 1

        # Calculate duration
        duration = time.perf_counter() - start_time

        # Log summary with metrics
        logger.info(
            f"Schema inference completed in {duration:.2f}s: "
            f"{len(schema)} columns from {len(sample_rows)} samples - "
            f"BOOL={type_distribution['BOOL']}, "
            f"INT64={type_distribution['INT64']}, "
            f"BIGNUMERIC={type_distribution['BIGNUMERIC']}, "
            f"DATE={type_distribution['DATE']}, "
            f"TIMESTAMP={type_distribution['TIMESTAMP']}, "
            f"STRING={type_distribution['STRING']}"
        )

        return schema
