"""Tests for BigQueryManager."""
from unittest.mock import Mock, patch

from google.api_core import exceptions as google_api_exceptions

from datawagon.bucket.bigquery_manager import BigQueryManager


def test_normalize_table_name_with_version() -> None:
    """Test table name normalization with version."""
    result = BigQueryManager.normalize_table_name("claim_raw", "v1-1")
    assert result == "claim_raw_v1_1"


def test_normalize_table_name_without_version() -> None:
    """Test table name normalization without version."""
    result = BigQueryManager.normalize_table_name("asset_raw", "")
    assert result == "asset_raw"


def test_normalize_table_name_complex_version() -> None:
    """Test table name normalization with complex version."""
    result = BigQueryManager.normalize_table_name("claim_raw", "v2-3-4")
    assert result == "claim_raw_v2_3_4"


@patch("datawagon.bucket.bigquery_manager.bigquery.Client")
def test_init_with_valid_dataset(mock_client_class: Mock) -> None:
    """Test BigQueryManager initializes successfully with valid dataset."""
    # Setup mock
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_dataset = Mock()
    mock_dataset.dataset_id = "test_dataset"
    mock_client.get_dataset.return_value = mock_dataset

    # Initialize manager
    manager = BigQueryManager(
        project_id="test-project",
        dataset_id="test_dataset",
        bucket_name="test-bucket",
    )

    # Assertions
    assert manager.has_error is False
    assert manager.project_id == "test-project"
    assert manager.dataset_id == "test_dataset"
    assert manager.bucket_name == "test-bucket"
    mock_client.get_dataset.assert_called_once_with("test-project.test_dataset")


@patch("datawagon.bucket.bigquery_manager.bigquery.Client")
def test_init_with_missing_dataset(mock_client_class: Mock) -> None:
    """Test BigQueryManager handles dataset not found error."""
    # Setup mock
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_client.get_dataset.side_effect = google_api_exceptions.NotFound("Not found")

    # Initialize manager
    manager = BigQueryManager(
        project_id="test-project",
        dataset_id="missing_dataset",
        bucket_name="test-bucket",
    )

    # Assertions
    assert manager.has_error is True


@patch("datawagon.bucket.bigquery_manager.bigquery.Client")
def test_init_with_auth_failure(mock_client_class: Mock) -> None:
    """Test BigQueryManager handles authentication failure."""
    # Setup mock
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_client.get_dataset.side_effect = google_api_exceptions.Unauthenticated(
        "Unauthenticated"
    )

    # Initialize manager
    manager = BigQueryManager(
        project_id="test-project",
        dataset_id="test_dataset",
        bucket_name="test-bucket",
    )

    # Assertions
    assert manager.has_error is True


@patch("datawagon.bucket.bigquery_manager.bigquery.Client")
def test_list_external_tables_empty(mock_client_class: Mock) -> None:
    """Test listing external tables returns empty list when none exist."""
    # Setup mock
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_dataset = Mock()
    mock_dataset.dataset_id = "test_dataset"
    mock_client.get_dataset.return_value = mock_dataset
    mock_client.list_tables.return_value = []

    # Initialize manager and list tables
    manager = BigQueryManager(
        project_id="test-project",
        dataset_id="test_dataset",
        bucket_name="test-bucket",
    )
    tables = manager.list_external_tables()

    # Assertions
    assert tables == []


@patch("datawagon.bucket.bigquery_manager.bigquery.Client")
def test_create_external_table_with_partitioning(mock_client_class: Mock) -> None:
    """Test creating external table with Hive partitioning."""
    # Setup mock
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_dataset = Mock()
    mock_dataset.dataset_id = "test_dataset"
    mock_client.get_dataset.return_value = mock_dataset
    mock_created_table = Mock()
    mock_created_table.full_table_id = "test-project.test_dataset.claim_raw_v1_1"
    mock_client.create_table.return_value = mock_created_table

    # Initialize manager and create table
    manager = BigQueryManager(
        project_id="test-project",
        dataset_id="test_dataset",
        bucket_name="test-bucket",
    )
    success = manager.create_external_table(
        table_name="claim_raw_v1_1",
        storage_folder_name="caravan-versioned/claim_raw_v1-1",
        use_hive_partitioning=True,
    )

    # Assertions
    assert success is True
    mock_client.create_table.assert_called_once()

    # Verify source URI has single wildcard (not double)
    call_args = mock_client.create_table.call_args
    table_arg = call_args[0][0]
    source_uris = table_arg.external_data_configuration.source_uris
    assert len(source_uris) == 1
    assert source_uris[0] == "gs://test-bucket/caravan-versioned/claim_raw_v1-1/*"
    # Ensure no double wildcard (report_date=*/*.csv.gz)
    assert "report_date=" not in source_uris[0]
    assert source_uris[0].count("*") == 1  # Only ONE wildcard


@patch("datawagon.bucket.bigquery_manager.bigquery.Client")
def test_create_external_table_already_exists(mock_client_class: Mock) -> None:
    """Test creating external table that already exists."""
    # Setup mock
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_dataset = Mock()
    mock_dataset.dataset_id = "test_dataset"
    mock_client.get_dataset.return_value = mock_dataset
    mock_client.create_table.side_effect = google_api_exceptions.Conflict("Conflict")

    # Initialize manager and attempt to create table
    manager = BigQueryManager(
        project_id="test-project",
        dataset_id="test_dataset",
        bucket_name="test-bucket",
    )
    success = manager.create_external_table(
        table_name="claim_raw_v1_1",
        storage_folder_name="caravan-versioned/claim_raw_v1-1",
    )

    # Assertions
    assert success is False


@patch("datawagon.bucket.bigquery_manager.bigquery.Client")
def test_table_exists_true(mock_client_class: Mock) -> None:
    """Test table_exists returns True when table exists."""
    # Setup mock
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_dataset = Mock()
    mock_dataset.dataset_id = "test_dataset"
    mock_client.get_dataset.return_value = mock_dataset
    mock_table = Mock()
    mock_client.get_table.return_value = mock_table

    # Initialize manager and check table existence
    manager = BigQueryManager(
        project_id="test-project",
        dataset_id="test_dataset",
        bucket_name="test-bucket",
    )
    exists = manager.table_exists("claim_raw_v1_1")

    # Assertions
    assert exists is True
    mock_client.get_table.assert_called_once_with(
        "test-project.test_dataset.claim_raw_v1_1"
    )


@patch("datawagon.bucket.bigquery_manager.bigquery.Client")
def test_table_exists_false(mock_client_class: Mock) -> None:
    """Test table_exists returns False when table does not exist."""
    # Setup mock
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_dataset = Mock()
    mock_dataset.dataset_id = "test_dataset"
    mock_client.get_dataset.return_value = mock_dataset
    mock_client.get_table.side_effect = google_api_exceptions.NotFound("Not found")

    # Initialize manager and check table existence
    manager = BigQueryManager(
        project_id="test-project",
        dataset_id="test_dataset",
        bucket_name="test-bucket",
    )
    exists = manager.table_exists("missing_table")

    # Assertions
    assert exists is False


def test_extract_partition_columns() -> None:
    """Test extracting partition columns from GCS URI pattern."""
    uri = "gs://bucket/folder/report_date=*/file.csv.gz"
    result = BigQueryManager._extract_partition_columns(uri)
    assert result == ["report_date"]


def test_extract_partition_columns_multiple() -> None:
    """Test extracting multiple partition columns."""
    uri = "gs://bucket/folder/year=*/month=*/file.csv.gz"
    result = BigQueryManager._extract_partition_columns(uri)
    assert result == ["year", "month"]


def test_extract_partition_columns_none() -> None:
    """Test extracting partition columns when none exist."""
    uri = "gs://bucket/folder/file.csv.gz"
    result = BigQueryManager._extract_partition_columns(uri)
    assert result == []
