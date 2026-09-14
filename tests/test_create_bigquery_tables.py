"""Tests for create_bigquery_tables command."""

from typing import Any, Dict, Generator, List
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner, Result

from datawagon.bucket.bigquery_manager import BigQueryManager
from datawagon.commands.create_bigquery_tables import _scan_gcs_storage_folders, create_bigquery_tables
from datawagon.objects.app_config import AppConfig
from datawagon.objects.bigquery_table_metadata import BigQueryTableInfo


def test_scan_folders_with_prefix() -> None:
    """Test that storage prefix filters folders correctly."""
    # Mock GcsManager to return blobs from multiple folders
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = [
        "caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/file.csv.gz",
        "caravan-versioned/asset_raw_v1-1/report_date=2023-07-31/file.csv.gz",
    ]

    # Scan with prefix - should only find versioned folders
    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="caravan-versioned")

    # Should find 2 folders under caravan-versioned
    assert len(folders) == 2
    folder_names = {f.storage_folder_name for f in folders}
    assert "caravan-versioned/claim_raw_v1-1" in folder_names
    assert "caravan-versioned/asset_raw_v1-1" in folder_names

    # Verify prefix was used in the call
    mock_gcs.list_all_blobs_with_prefix.assert_called_once_with(prefix="caravan-versioned")


def test_scan_folders_without_prefix() -> None:
    """Test scanning all folders when no prefix is specified."""
    # Mock GcsManager to return blobs from multiple top-level folders
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = [
        "caravan/claim_raw/file1.csv.gz",
        "caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/file2.csv.gz",
    ]

    # Scan without prefix (empty string) - should find all folders
    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="")

    # Should find 2 folders (one in caravan, one in caravan-versioned)
    assert len(folders) == 2
    folder_names = {f.storage_folder_name for f in folders}
    assert "caravan/claim_raw" in folder_names
    assert "caravan-versioned/claim_raw_v1-1" in folder_names

    # Verify empty prefix was used in the call
    mock_gcs.list_all_blobs_with_prefix.assert_called_once_with(prefix="")


def test_scan_folders_with_nonexistent_prefix() -> None:
    """Test that non-existent prefix returns empty list."""
    # Mock GcsManager to return empty list (prefix doesn't match anything)
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = []

    # Scan with non-existent prefix
    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="nonexistent-prefix")

    # Should return empty list
    assert len(folders) == 0

    # Verify prefix was used in the call
    mock_gcs.list_all_blobs_with_prefix.assert_called_once_with(prefix="nonexistent-prefix")


def test_scan_folders_extracts_version() -> None:
    """Test that folder scanning correctly extracts version information."""
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = [
        "caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/file.csv.gz",
    ]

    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="caravan-versioned")

    assert len(folders) == 1
    folder = folders[0]
    assert folder.table_name == "claim_raw"
    assert folder.file_version == "v1-1"
    assert folder.proposed_bq_table_name == "claim_raw_v1_1"


def test_scan_folders_detects_partitioning() -> None:
    """Test that folder scanning detects Hive partitioning."""
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = [
        "caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/file.csv.gz",
    ]

    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="caravan-versioned")

    assert len(folders) == 1
    assert folders[0].has_partitioning is True


def test_scan_folders_without_partitioning() -> None:
    """Test that folder scanning correctly identifies non-partitioned folders."""
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = [
        "caravan-versioned/simple_table/file.csv.gz",
    ]

    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="caravan-versioned")

    assert len(folders) == 1
    assert folders[0].has_partitioning is False


# --- create-bigquery-tables command ---

MODULE = "datawagon.commands.create_bigquery_tables"


@pytest.fixture
def ctx_obj() -> Dict[str, Any]:
    app_config = AppConfig(
        csv_source_dir="/tmp",
        csv_source_config="/tmp/config.toml",
        gcs_project_id="project",
        gcs_bucket="bucket",
        bq_dataset="dataset",
        bq_storage_prefix="prefix",
    )
    return {"CONFIG": app_config}


@pytest.fixture
def mocks() -> Generator[Dict[str, Any], None, None]:
    """Patch GCS/BQ manager classes and list_bigquery_tables in the command module."""
    with (
        patch(f"{MODULE}.GcsManager") as gcs_class,
        patch(f"{MODULE}.BigQueryManager") as bq_class,
        patch(f"{MODULE}.list_bigquery_tables") as list_tables,
    ):
        # _scan_gcs_storage_folders calls the real static method via the patched class
        bq_class.normalize_table_name.side_effect = BigQueryManager.normalize_table_name
        gcs = Mock(has_error=False)
        gcs.list_all_blobs_with_prefix.return_value = [
            "prefix/claim_raw_v1-1/report_date=2023-06-30/a.csv.gz",
            "prefix/claim_raw_v1-1/report_date=2023-07-31/b.csv.gz",
            "prefix/asset_raw_v1-1/c.csv.gz",
            "prefix/asset_raw_v1-1/notes.txt",
        ]
        gcs_class.return_value = gcs
        bq = Mock(has_error=False)
        bq.create_external_table.return_value = True
        bq_class.return_value = bq
        list_tables.return_value = []
        yield {"gcs_class": gcs_class, "gcs": gcs, "bq_class": bq_class, "bq": bq, "list_tables": list_tables}


def _existing(name: str) -> BigQueryTableInfo:
    return BigQueryTableInfo(table_name=name, dataset_id="dataset", project_id="project", source_uri_pattern="gs://x")


def _invoke(ctx_obj: Dict[str, Any], args: List[str] | None = None, confirm: str = "y\n") -> Result:
    return CliRunner().invoke(create_bigquery_tables, args or [], obj=ctx_obj, input=confirm)


def test_command_creates_missing_tables(ctx_obj: Dict[str, Any], mocks: Dict[str, Any]) -> None:
    mocks["list_tables"].return_value = [_existing("asset_raw_v1_1")]

    result = _invoke(ctx_obj)

    assert result.exit_code == 0, result.output
    mocks["gcs_class"].assert_called_once_with("project", "bucket")
    mocks["gcs"].list_all_blobs_with_prefix.assert_called_once_with(prefix="prefix")
    mocks["bq_class"].assert_called_once_with("project", "dataset", "bucket")
    mocks["bq"].create_external_table.assert_called_once_with(
        table_name="claim_raw_v1_1",
        storage_folder_name="prefix/claim_raw_v1-1",
        use_hive_partitioning=True,
    )
    assert "Found 2 storage folders" in result.output
    assert "Successfully created 1 external tables" in result.output
    assert ctx_obj["GCS_MANAGER"] is mocks["gcs"]
    assert ctx_obj["BQ_MANAGER"] is mocks["bq"]


def test_command_dataset_option_overrides_config(ctx_obj: Dict[str, Any], mocks: Dict[str, Any]) -> None:
    result = _invoke(ctx_obj, ["--dataset", "other_ds"])

    assert result.exit_code == 0, result.output
    assert mocks["list_tables"].call_args.kwargs == {"dataset": "other_ds"}
    mocks["bq_class"].assert_called_once_with("project", "other_ds", "bucket")
    assert mocks["bq"].create_external_table.call_count == 2


def test_command_reports_partial_failures(ctx_obj: Dict[str, Any], mocks: Dict[str, Any]) -> None:
    mocks["bq"].create_external_table.side_effect = [True, False]

    result = _invoke(ctx_obj)

    assert result.exit_code == 0, result.output
    # Folders are created in sorted table-name order, unpartitioned asset folder first
    calls = mocks["bq"].create_external_table.call_args_list
    assert [c.kwargs["table_name"] for c in calls] == ["asset_raw_v1_1", "claim_raw_v1_1"]
    assert calls[0].kwargs["use_hive_partitioning"] is False
    assert "Created 1 tables, 1 errors" in result.output


def test_command_declined_confirmation_creates_nothing(ctx_obj: Dict[str, Any], mocks: Dict[str, Any]) -> None:
    result = _invoke(ctx_obj, confirm="n\n")

    assert result.exit_code == 1
    assert "Aborted" in result.output
    mocks["bq"].create_external_table.assert_not_called()


def test_command_all_tables_exist(ctx_obj: Dict[str, Any], mocks: Dict[str, Any]) -> None:
    mocks["list_tables"].return_value = [_existing("asset_raw_v1_1"), _existing("claim_raw_v1_1")]

    result = _invoke(ctx_obj, confirm="")

    assert result.exit_code == 0, result.output
    assert "already have corresponding BigQuery tables" in result.output
    mocks["bq"].create_external_table.assert_not_called()


def test_command_no_storage_folders(ctx_obj: Dict[str, Any], mocks: Dict[str, Any]) -> None:
    mocks["gcs"].list_all_blobs_with_prefix.return_value = ["prefix/readme.txt"]

    result = _invoke(ctx_obj, confirm="")

    assert result.exit_code == 0, result.output
    assert "No storage folders found" in result.output
    mocks["bq"].create_external_table.assert_not_called()


def test_command_gcs_connection_error_aborts(ctx_obj: Dict[str, Any], mocks: Dict[str, Any]) -> None:
    mocks["gcs"].has_error = True

    result = _invoke(ctx_obj)

    assert result.exit_code == 1
    assert "Unable to connect to GCS" in result.output
    mocks["list_tables"].assert_not_called()
    mocks["bq_class"].assert_not_called()


def test_command_bigquery_connection_error_aborts(ctx_obj: Dict[str, Any], mocks: Dict[str, Any]) -> None:
    mocks["bq"].has_error = True

    result = _invoke(ctx_obj)

    assert result.exit_code == 1
    assert "Failed to connect to BigQuery" in result.output
    mocks["gcs"].list_all_blobs_with_prefix.assert_not_called()
    mocks["bq"].create_external_table.assert_not_called()


def test_command_reuses_managers_from_context(ctx_obj: Dict[str, Any], mocks: Dict[str, Any]) -> None:
    ctx_obj["GCS_MANAGER"] = mocks["gcs"]
    ctx_obj["BQ_MANAGER"] = mocks["bq"]

    result = _invoke(ctx_obj)

    assert result.exit_code == 0, result.output
    mocks["gcs_class"].assert_not_called()
    mocks["bq_class"].assert_not_called()
    assert mocks["bq"].create_external_table.call_count == 2
