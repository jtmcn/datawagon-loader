"""Tests for recreate-bigquery-tables command."""

from typing import Any
from unittest.mock import Mock, patch

from click.testing import CliRunner

from datawagon.commands.recreate_bigquery_tables import recreate_bigquery_tables
from datawagon.objects.app_config import AppConfig
from datawagon.objects.bigquery_table_metadata import BigQueryTableInfo


@patch("datawagon.commands.recreate_bigquery_tables.BigQueryManager")
@patch("datawagon.commands.recreate_bigquery_tables.GcsManager")
@patch("datawagon.commands.recreate_bigquery_tables.list_bigquery_tables")
def test_recreate_tables_with_force(
    mock_list_tables: Any, mock_gcs_manager_class: Any, mock_bq_manager_class: Any
) -> None:
    """Test recreating tables with --force flag."""
    # Setup mocks
    mock_table = BigQueryTableInfo(
        table_name="test_table",
        dataset_id="dataset",
        project_id="project",
        source_uri_pattern="gs://bucket/folder/report_date=*/*.csv.gz",
        is_partitioned=True,
        partition_columns=["report_date"],
    )

    mock_list_tables.return_value = [mock_table]

    # Mock GCS manager
    mock_gcs = Mock()
    mock_gcs.has_error = False
    mock_gcs_manager_class.return_value = mock_gcs

    # Mock BigQuery manager
    mock_bq = Mock()
    mock_bq.has_error = False
    mock_bq.delete_table.return_value = True
    mock_bq.create_external_table.return_value = True
    mock_bq_manager_class.return_value = mock_bq

    # Create test config
    app_config = AppConfig(
        csv_source_dir="/tmp",
        csv_source_config="/tmp/config.toml",
        gcs_project_id="project",
        gcs_bucket="bucket",
        bq_dataset="dataset",
        bq_storage_prefix="folder",
    )

    ctx_obj = {"CONFIG": app_config}

    # Run command with --force
    runner = CliRunner()
    result = runner.invoke(
        recreate_bigquery_tables,
        ["--force"],
        obj=ctx_obj,
    )

    # Assertions
    assert result.exit_code == 0
    mock_bq.delete_table.assert_called_once_with("test_table")
    mock_bq.create_external_table.assert_called_once()

    # Verify create was called with correct parameters
    call_args = mock_bq.create_external_table.call_args
    assert call_args[1]["table_name"] == "test_table"
    assert call_args[1]["storage_folder_name"] == "folder"
    assert call_args[1]["use_hive_partitioning"] is True


@patch("datawagon.commands.recreate_bigquery_tables.BigQueryManager")
@patch("datawagon.commands.recreate_bigquery_tables.GcsManager")
@patch("datawagon.commands.recreate_bigquery_tables.list_bigquery_tables")
def test_recreate_tables_no_tables_found(
    mock_list_tables: Any, mock_gcs_manager_class: Any, mock_bq_manager_class: Any
) -> None:
    """Test recreating when no tables exist."""
    mock_list_tables.return_value = []

    # Mock managers
    mock_gcs = Mock()
    mock_gcs.has_error = False
    mock_gcs_manager_class.return_value = mock_gcs

    mock_bq = Mock()
    mock_bq.has_error = False
    mock_bq_manager_class.return_value = mock_bq

    # Create test config
    app_config = AppConfig(
        csv_source_dir="/tmp",
        csv_source_config="/tmp/config.toml",
        gcs_project_id="project",
        gcs_bucket="bucket",
        bq_dataset="dataset",
        bq_storage_prefix="folder",
    )

    ctx_obj = {"CONFIG": app_config}

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        recreate_bigquery_tables,
        ["--force"],
        obj=ctx_obj,
    )

    # Assertions
    assert result.exit_code == 0
    assert "No external tables found" in result.output
    mock_bq.delete_table.assert_not_called()
    mock_bq.create_external_table.assert_not_called()


@patch("datawagon.commands.recreate_bigquery_tables.BigQueryManager")
@patch("datawagon.commands.recreate_bigquery_tables.GcsManager")
@patch("datawagon.commands.recreate_bigquery_tables.list_bigquery_tables")
def test_recreate_specific_tables(
    mock_list_tables: Any, mock_gcs_manager_class: Any, mock_bq_manager_class: Any
) -> None:
    """Test recreating specific tables with --tables option."""
    # Setup multiple tables
    table1 = BigQueryTableInfo(
        table_name="table_one",
        dataset_id="dataset",
        project_id="project",
        source_uri_pattern="gs://bucket/folder1/*",
        is_partitioned=False,
    )
    table2 = BigQueryTableInfo(
        table_name="table_two",
        dataset_id="dataset",
        project_id="project",
        source_uri_pattern="gs://bucket/folder2/*",
        is_partitioned=False,
    )

    mock_list_tables.return_value = [table1, table2]

    # Mock managers
    mock_gcs = Mock()
    mock_gcs.has_error = False
    mock_gcs_manager_class.return_value = mock_gcs

    mock_bq = Mock()
    mock_bq.has_error = False
    mock_bq.delete_table.return_value = True
    mock_bq.create_external_table.return_value = True
    mock_bq_manager_class.return_value = mock_bq

    # Create test config
    app_config = AppConfig(
        csv_source_dir="/tmp",
        csv_source_config="/tmp/config.toml",
        gcs_project_id="project",
        gcs_bucket="bucket",
        bq_dataset="dataset",
        bq_storage_prefix="folder",
    )

    ctx_obj = {"CONFIG": app_config}

    # Run command with --tables option
    runner = CliRunner()
    result = runner.invoke(
        recreate_bigquery_tables,
        ["--force", "--tables", "table_one"],
        obj=ctx_obj,
    )

    # Assertions
    assert result.exit_code == 0
    # Should only delete and recreate table_one
    mock_bq.delete_table.assert_called_once_with("table_one")
    assert mock_bq.create_external_table.call_count == 1


@patch("datawagon.commands.recreate_bigquery_tables.BigQueryManager")
@patch("datawagon.commands.recreate_bigquery_tables.GcsManager")
@patch("datawagon.commands.recreate_bigquery_tables.list_bigquery_tables")
def test_recreate_handles_delete_failure(
    mock_list_tables: Any, mock_gcs_manager_class: Any, mock_bq_manager_class: Any
) -> None:
    """Test handling when delete fails."""
    mock_table = BigQueryTableInfo(
        table_name="test_table",
        dataset_id="dataset",
        project_id="project",
        source_uri_pattern="gs://bucket/folder/*",
        is_partitioned=False,
    )

    mock_list_tables.return_value = [mock_table]

    # Mock managers
    mock_gcs = Mock()
    mock_gcs.has_error = False
    mock_gcs_manager_class.return_value = mock_gcs

    # Mock delete failure
    mock_bq = Mock()
    mock_bq.has_error = False
    mock_bq.delete_table.return_value = False  # Delete fails
    mock_bq_manager_class.return_value = mock_bq

    # Create test config
    app_config = AppConfig(
        csv_source_dir="/tmp",
        csv_source_config="/tmp/config.toml",
        gcs_project_id="project",
        gcs_bucket="bucket",
        bq_dataset="dataset",
        bq_storage_prefix="folder",
    )

    ctx_obj = {"CONFIG": app_config}

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        recreate_bigquery_tables,
        ["--force"],
        obj=ctx_obj,
    )

    # Assertions
    assert result.exit_code == 0
    mock_bq.delete_table.assert_called_once()
    # Should not call create_external_table since delete failed
    mock_bq.create_external_table.assert_not_called()
    assert "errors" in result.output.lower()


@patch("datawagon.commands.recreate_bigquery_tables.BigQueryManager")
@patch("datawagon.commands.recreate_bigquery_tables.GcsManager")
@patch("datawagon.commands.recreate_bigquery_tables.list_bigquery_tables")
def test_recreate_extracts_storage_folder_correctly(
    mock_list_tables: Any, mock_gcs_manager_class: Any, mock_bq_manager_class: Any
) -> None:
    """Test that storage folder is extracted correctly from source URI."""
    # Test with partitioned URI
    mock_table = BigQueryTableInfo(
        table_name="test_table",
        dataset_id="dataset",
        project_id="project",
        source_uri_pattern="gs://bucket/prefix/subfolder/report_date=*/*.csv.gz",
        is_partitioned=True,
        partition_columns=["report_date"],
    )

    mock_list_tables.return_value = [mock_table]

    # Mock managers
    mock_gcs = Mock()
    mock_gcs.has_error = False
    mock_gcs_manager_class.return_value = mock_gcs

    mock_bq = Mock()
    mock_bq.has_error = False
    mock_bq.delete_table.return_value = True
    mock_bq.create_external_table.return_value = True
    mock_bq_manager_class.return_value = mock_bq

    # Create test config
    app_config = AppConfig(
        csv_source_dir="/tmp",
        csv_source_config="/tmp/config.toml",
        gcs_project_id="project",
        gcs_bucket="bucket",
        bq_dataset="dataset",
        bq_storage_prefix="prefix",
    )

    ctx_obj = {"CONFIG": app_config}

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        recreate_bigquery_tables,
        ["--force"],
        obj=ctx_obj,
    )

    # Assertions
    assert result.exit_code == 0

    # Verify storage folder was extracted correctly
    call_args = mock_bq.create_external_table.call_args
    assert call_args[1]["storage_folder_name"] == "prefix/subfolder"
