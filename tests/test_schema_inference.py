"""Tests for schema inference."""

import gzip
from io import BytesIO
from typing import Any
from unittest.mock import Mock, patch

from google.cloud import bigquery

from datawagon.bucket.schema_inference import SchemaInferenceManager


def test_normalize_column_names_basic() -> None:
    """Test basic column name normalization."""
    columns = ["Asset ID", "Revenue (USD)", "Date"]
    result = SchemaInferenceManager.normalize_column_names(columns)
    # Parentheses are removed (not replaced), so (USD) becomes _usd not _usd_
    assert result == ["asset_id", "revenue__usd", "date"]


def test_normalize_column_names_special_chars() -> None:
    """Test normalization with special characters."""
    columns = ["Col-Name", "Col/Path", "Col.Dot", "Col:Time", "Col?Query"]
    result = SchemaInferenceManager.normalize_column_names(columns)
    # : and ? are removed (not replaced with _)
    assert result == ["col_name", "col_path", "col_dot", "coltime", "colquery"]


def test_normalize_column_names_duplicates() -> None:
    """Test handling of duplicate column names."""
    columns = ["ID", "id", "ID "]
    result = SchemaInferenceManager.normalize_column_names(columns)
    # "ID" -> "id", "id" -> "id_1", "ID " -> "id_" (space becomes _)
    assert result == ["id", "id_1", "id_"]


def test_normalize_column_names_parentheses() -> None:
    """Test handling of parentheses in column names."""
    columns = ["Revenue(USD)", "Count(Total)"]
    result = SchemaInferenceManager.normalize_column_names(columns)
    assert result == ["revenue_usd", "count_total"]


@patch("datawagon.bucket.schema_inference.storage.Client")
def test_read_csv_header_success(mock_storage_client: Any) -> None:
    """Test successful CSV header reading."""
    # Create mock CSV data
    csv_content = "Asset ID,Revenue,Date\nval1,val2,val3\n"
    gzipped = BytesIO()
    with gzip.open(gzipped, mode="wt", encoding="utf-8") as f:
        f.write(csv_content)
    gzipped_data = gzipped.getvalue()

    # Mock GCS blob
    mock_blob = Mock()
    mock_blob.name = "test/file.csv.gz"

    def mock_download(file_obj: Any) -> None:
        file_obj.write(gzipped_data)

    mock_blob.download_to_file = mock_download

    mock_bucket = Mock()
    mock_bucket.list_blobs.return_value = [mock_blob]

    mock_client = Mock()
    mock_client.bucket.return_value = mock_bucket

    # Test
    manager = SchemaInferenceManager(mock_client, "test-bucket")
    header = manager.read_csv_header_from_gcs("test-folder")

    assert header == ["Asset ID", "Revenue", "Date"]


@patch("datawagon.bucket.schema_inference.storage.Client")
def test_read_csv_header_with_invalid_row(mock_storage_client: Any) -> None:
    """Test CSV header reading when first row has single column."""
    # Create mock CSV data with invalid first row
    csv_content = "Invalid Single Column\nAsset ID,Revenue,Date\nval1,val2,val3\n"
    gzipped = BytesIO()
    with gzip.open(gzipped, mode="wt", encoding="utf-8") as f:
        f.write(csv_content)
    gzipped_data = gzipped.getvalue()

    # Mock GCS blob
    mock_blob = Mock()
    mock_blob.name = "test/file.csv.gz"

    def mock_download(file_obj: Any) -> None:
        file_obj.write(gzipped_data)

    mock_blob.download_to_file = mock_download

    mock_bucket = Mock()
    mock_bucket.list_blobs.return_value = [mock_blob]

    mock_client = Mock()
    mock_client.bucket.return_value = mock_bucket

    # Test
    manager = SchemaInferenceManager(mock_client, "test-bucket")
    header = manager.read_csv_header_from_gcs("test-folder")

    # Should skip the invalid row and return the real header
    assert header == ["Asset ID", "Revenue", "Date"]


@patch("datawagon.bucket.schema_inference.storage.Client")
def test_read_csv_header_no_files(mock_storage_client: Any) -> None:
    """Test reading header when no CSV files exist."""
    mock_bucket = Mock()
    mock_bucket.list_blobs.return_value = []

    mock_client = Mock()
    mock_client.bucket.return_value = mock_bucket

    manager = SchemaInferenceManager(mock_client, "test-bucket")
    header = manager.read_csv_header_from_gcs("empty-folder")

    assert header is None


@patch("datawagon.bucket.schema_inference.storage.Client")
def test_infer_schema_creates_string_fields(mock_storage_client: Any) -> None:
    """Test schema inference creates STRING fields when no sample data."""
    # Mock header reading with no sample rows
    mock_client = Mock()
    manager = SchemaInferenceManager(mock_client, "test-bucket")

    with patch.object(manager, "read_csv_header_and_sample") as mock_read:
        # Return header with no sample rows (fallback to all-STRING)
        mock_read.return_value = (["Asset ID", "Revenue", "Date"], [])

        schema = manager.infer_schema("test-folder")

        assert len(schema) == 3  # type: ignore[arg-type]
        assert all(isinstance(f, bigquery.SchemaField) for f in schema)  # type: ignore[union-attr]
        assert all(f.field_type == "STRING" for f in schema)  # type: ignore[union-attr]
        assert [f.name for f in schema] == ["asset_id", "revenue", "date"]  # type: ignore[union-attr]


@patch("datawagon.bucket.schema_inference.storage.Client")
def test_infer_schema_handles_no_header(mock_storage_client: Any) -> None:
    """Test schema inference when data reading fails."""
    mock_client = Mock()
    manager = SchemaInferenceManager(mock_client, "test-bucket")

    with patch.object(manager, "read_csv_header_and_sample") as mock_read:
        mock_read.return_value = None

        schema = manager.infer_schema("test-folder")

        assert schema is None


@patch("datawagon.bucket.schema_inference.storage.Client")
def test_infer_schema_with_special_characters(mock_storage_client: Any) -> None:
    """Test schema inference with columns containing special characters."""
    mock_client = Mock()
    manager = SchemaInferenceManager(mock_client, "test-bucket")

    with patch.object(manager, "read_csv_header_and_sample") as mock_read:
        # Return header with no sample rows (fallback to all-STRING)
        mock_read.return_value = (["Asset ID", "Revenue (USD)", "Date-Time", "Views/Clicks"], [])

        schema = manager.infer_schema("test-folder")

        assert len(schema) == 4  # type: ignore[arg-type]
        # Parentheses are removed, not replaced with _
        expected_names = ["asset_id", "revenue__usd", "date_time", "views_clicks"]  # type: ignore[union-attr]
        assert [f.name for f in schema] == expected_names  # type: ignore[union-attr]
        assert all(f.field_type == "STRING" for f in schema)  # type: ignore[union-attr]
        assert all(f.mode == "NULLABLE" for f in schema)  # type: ignore[union-attr]


# ============================================================================
# Type Detection Helper Tests
# ============================================================================


def test_try_parse_bool_valid() -> None:
    """Test boolean parsing with valid values."""
    valid_bools = ["true", "false", "TRUE", "FALSE", "yes", "no", "YES", "NO", "1", "0", "  true  ", "  1  "]
    for value in valid_bools:
        assert SchemaInferenceManager._try_parse_bool(value) is True, f"Failed for: {value}"


def test_try_parse_bool_invalid() -> None:
    """Test boolean parsing with invalid values."""
    invalid_bools = ["", "2", "123", "maybe", "True1", "yes!", "null"]
    for value in invalid_bools:
        assert SchemaInferenceManager._try_parse_bool(value) is False, f"Failed for: {value}"


def test_try_parse_int_valid() -> None:
    """Test integer parsing with valid values."""
    valid_ints = ["123", "-456", "0", "  789  ", str(2**62), str(-(2**62))]
    for value in valid_ints:
        assert SchemaInferenceManager._try_parse_int(value) is True, f"Failed for: {value}"


def test_try_parse_int_leading_zeros() -> None:
    """Test that integers with leading zeros are rejected."""
    leading_zero_cases = ["00123", "0001", "007"]
    for value in leading_zero_cases:
        assert SchemaInferenceManager._try_parse_int(value) is False, f"Failed for: {value}"


def test_try_parse_int_overflow() -> None:
    """Test that integers outside INT64 range are rejected."""
    overflow_cases = [
        str(2**63),  # INT64_MAX + 1
        str(-(2**63) - 1),  # INT64_MIN - 1
        "9999999999999999999999",  # Way too large
    ]
    for value in overflow_cases:
        assert SchemaInferenceManager._try_parse_int(value) is False, f"Failed for: {value}"


def test_try_parse_int_invalid() -> None:
    """Test integer parsing with invalid values."""
    invalid_ints = ["", "123.45", "1e10", "abc", "123abc", "null"]
    for value in invalid_ints:
        assert SchemaInferenceManager._try_parse_int(value) is False, f"Failed for: {value}"


def test_try_parse_float_valid() -> None:
    """Test float parsing with valid values."""
    valid_floats = ["123.45", "-456.78", "1e10", "1.0", ".5", "3.14159", "  2.718  "]
    for value in valid_floats:
        assert SchemaInferenceManager._try_parse_float(value) is True, f"Failed for: {value}"


def test_try_parse_float_excludes_ints() -> None:
    """Test that float parsing excludes valid integers."""
    int_cases = ["123", "-456", "0"]
    for value in int_cases:
        assert SchemaInferenceManager._try_parse_float(value) is False, f"Failed for: {value}"


def test_try_parse_float_invalid() -> None:
    """Test float parsing with invalid values."""
    invalid_floats = ["", "abc", "123abc", "null"]
    for value in invalid_floats:
        assert SchemaInferenceManager._try_parse_float(value) is False, f"Failed for: {value}"


def test_try_parse_date_valid_dates() -> None:
    """Test date parsing with valid DATE formats."""
    valid_dates = ["2023-06-30", "2024-01-01", "  2023-12-31  ", "2023/06/30", "2024/01/01"]
    for value in valid_dates:
        result = SchemaInferenceManager._try_parse_date(value)
        assert result == "DATE", f"Failed for: {value}, got: {result}"


def test_try_parse_date_valid_timestamps() -> None:
    """Test date parsing with valid TIMESTAMP formats."""
    valid_timestamps = [
        "2023-06-30 12:00:00",
        "2024-01-01 23:59:59",
        "2023-12-31 00:00:00.123",
        "  2023-06-30 12:00:00  ",
        "2023/06/30 12:00:00",
        "2024/01/01 23:59:59.456",
    ]
    for value in valid_timestamps:
        result = SchemaInferenceManager._try_parse_date(value)
        assert result == "TIMESTAMP", f"Failed for: {value}, got: {result}"


def test_try_parse_date_invalid() -> None:
    """Test date parsing with invalid formats."""
    # Note: Regex validates format only, not actual calendar values
    # BigQuery will validate actual date values during load
    invalid_dates = [
        "",
        "06/30/2023",  # Wrong format (MM/DD/YYYY)
        "2023-6-30",  # Missing leading zero
        "2023-6-3",  # Missing leading zeros
        "abc",
        "null",
        "123",
        "2023",
    ]
    for value in invalid_dates:
        result = SchemaInferenceManager._try_parse_date(value)
        assert result is None, f"Failed for: {value}, got: {result}"


# ============================================================================
# Column Type Inference Tests
# ============================================================================


def test_infer_column_type_all_int() -> None:
    """Test column type inference with all integer values."""
    sample_rows = [[str(i), "other"] for i in range(1, 101)]
    manager = SchemaInferenceManager(Mock(), "test-bucket")

    result = manager.infer_column_type("test_col", 0, sample_rows)
    assert result == "INT64"


def test_infer_column_type_all_float() -> None:
    """Test column type inference with all float values."""
    sample_rows = [[f"{i}.5", "other"] for i in range(1, 101)]
    manager = SchemaInferenceManager(Mock(), "test-bucket")

    result = manager.infer_column_type("test_col", 0, sample_rows)
    assert result == "FLOAT64"


def test_infer_column_type_all_bool() -> None:
    """Test column type inference with all boolean values."""
    sample_rows = [["true", "other"] if i % 2 == 0 else ["false", "other"] for i in range(100)]
    manager = SchemaInferenceManager(Mock(), "test-bucket")

    result = manager.infer_column_type("test_col", 0, sample_rows)
    assert result == "BOOL"


def test_infer_column_type_all_date() -> None:
    """Test column type inference with all date values."""
    sample_rows = [["2023-06-30", "other"] for _ in range(100)]
    manager = SchemaInferenceManager(Mock(), "test-bucket")

    result = manager.infer_column_type("test_col", 0, sample_rows)
    assert result == "DATE"


def test_infer_column_type_all_timestamp() -> None:
    """Test column type inference with all timestamp values."""
    sample_rows = [["2023-06-30 12:00:00", "other"] for _ in range(100)]
    manager = SchemaInferenceManager(Mock(), "test-bucket")

    result = manager.infer_column_type("test_col", 0, sample_rows)
    assert result == "TIMESTAMP"


def test_infer_column_type_mixed_below_threshold() -> None:
    """Test that mixed types below 95% threshold fall back to STRING."""
    # 90 integers + 10 strings = 90% confidence (below 95%)
    sample_rows = [[str(i), "other"] for i in range(1, 91)] + [["abc", "other"] for _ in range(10)]
    manager = SchemaInferenceManager(Mock(), "test-bucket")

    result = manager.infer_column_type("test_col", 0, sample_rows)
    assert result == "STRING"


def test_infer_column_type_mostly_null() -> None:
    """Test that columns with insufficient non-null values fall back to STRING."""
    # Only 5 non-null values (below min_non_null_samples=10)
    sample_rows = [["123", "other"] for _ in range(5)] + [["", "other"] for _ in range(95)]
    manager = SchemaInferenceManager(Mock(), "test-bucket")

    result = manager.infer_column_type("test_col", 0, sample_rows)
    assert result == "STRING"


def test_infer_column_type_skips_empty_values() -> None:
    """Test that empty values and nulls are skipped during type detection."""
    # 50 valid ints + 50 nulls/empty = should still detect INT64
    sample_rows = (
        [[str(i), "other"] for i in range(1, 51)]
        + [["", "other"] for _ in range(25)]
        + [["null", "other"] for _ in range(25)]
    )
    manager = SchemaInferenceManager(Mock(), "test-bucket")

    result = manager.infer_column_type("test_col", 0, sample_rows)
    assert result == "INT64"


def test_infer_column_type_ragged_rows() -> None:
    """Test handling of rows with fewer columns than expected."""
    # Some rows don't have column at index 1
    sample_rows = [["123", "456"] for _ in range(50)] + [["789"] for _ in range(50)]
    manager = SchemaInferenceManager(Mock(), "test-bucket")

    # Should handle missing column gracefully
    result = manager.infer_column_type("test_col", 1, sample_rows)
    # Only 50 values available, should detect INT64
    assert result == "INT64"


# ============================================================================
# Integration Tests
# ============================================================================


@patch("datawagon.bucket.schema_inference.storage.Client")
def test_read_csv_header_and_sample_returns_sample_rows(mock_storage_client: Any) -> None:
    """Test that read_csv_header_and_sample returns header and sample rows."""
    # Create mock CSV data with header + 5 data rows
    csv_content = "Col1,Col2,Col3\n" + "\n".join([f"val{i}1,val{i}2,val{i}3" for i in range(5)])
    gzipped = BytesIO()
    with gzip.open(gzipped, mode="wt", encoding="utf-8") as f:
        f.write(csv_content)
    gzipped_data = gzipped.getvalue()

    # Mock GCS blob
    mock_blob = Mock()
    mock_blob.name = "test/file.csv.gz"

    def mock_download(file_obj: Any) -> None:
        file_obj.write(gzipped_data)

    mock_blob.download_to_file = mock_download

    mock_bucket = Mock()
    mock_bucket.list_blobs.return_value = [mock_blob]

    mock_client = Mock()
    mock_client.bucket.return_value = mock_bucket

    # Test
    manager = SchemaInferenceManager(mock_client, "test-bucket")
    result = manager.read_csv_header_and_sample("test-folder", sample_size=3)

    assert result is not None
    header, sample_rows = result
    assert header == ["Col1", "Col2", "Col3"]
    assert len(sample_rows) == 3  # Should only read 3 rows (requested sample_size)
    assert sample_rows[0] == ["val01", "val02", "val03"]


@patch("datawagon.bucket.schema_inference.storage.Client")
def test_infer_schema_with_mixed_types(mock_storage_client: Any) -> None:
    """Test full schema inference with mixed column types."""
    mock_client = Mock()
    manager = SchemaInferenceManager(mock_client, "test-bucket")

    # Mock data with different types per column
    header = ["id", "name", "count", "price", "active", "created_date"]
    sample_rows = [
        ["1", "Alice", "100", "19.99", "true", "2023-06-30"],
        ["2", "Bob", "200", "29.99", "false", "2023-07-01"],
        ["3", "Charlie", "300", "39.99", "true", "2023-07-02"],
    ] * 34  # Repeat to get 102 rows (>95% confidence)

    with patch.object(manager, "read_csv_header_and_sample") as mock_read:
        mock_read.return_value = (header, sample_rows)

        schema = manager.infer_schema("test-folder")

        assert len(schema) == 6  # type: ignore[arg-type]
        assert schema[0].name == "id"  # type: ignore[index]
        assert schema[0].field_type == "INT64"  # type: ignore[index]
        assert schema[1].name == "name"  # type: ignore[index]
        assert schema[1].field_type == "STRING"  # type: ignore[index]
        assert schema[2].name == "count"  # type: ignore[index]
        assert schema[2].field_type == "INT64"  # type: ignore[index]
        assert schema[3].name == "price"  # type: ignore[index]
        assert schema[3].field_type == "FLOAT64"  # type: ignore[index]
        assert schema[4].name == "active"  # type: ignore[index]
        assert schema[4].field_type == "BOOL"  # type: ignore[index]
        assert schema[5].name == "created_date"  # type: ignore[index]
        assert schema[5].field_type == "DATE"  # type: ignore[index]
