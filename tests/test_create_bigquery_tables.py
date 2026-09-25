"""Tests for create_bigquery_tables command."""

import re
from typing import Any, Dict, Generator, List
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner, Result

from datawagon.commands.create_bigquery_tables import create_bigquery_tables
from datawagon.objects.app_config import AppConfig
from datawagon.objects.bigquery_table_metadata import BigQueryTableInfo
from datawagon.objects.storage_layout import StorageLayout

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
    )
    return {"CONFIG": app_config, "STORAGE_LAYOUT": StorageLayout("prefix", frozenset({"claim_raw", "asset_raw"}))}


@pytest.fixture
def mocks() -> Generator[Dict[str, Any], None, None]:
    """Patch GCS/BQ manager classes and list_bigquery_tables in the command module."""
    with (
        patch(f"{MODULE}.GcsManager") as gcs_class,
        patch(f"{MODULE}.BigQueryManager") as bq_class,
        patch(f"{MODULE}.list_bigquery_tables") as list_tables,
    ):
        gcs = Mock(has_error=False)
        gcs.list_all_blobs_with_prefix.return_value = [
            "prefix/claim_raw_v1-1/report_date=2023-06-30/a.csv.gz",
            "prefix/claim_raw_v1-1/report_date=2023-07-31/b.csv.gz",
            "prefix/asset_raw_v1-1/report_date=2023-06-30/c.csv.gz",
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
    calls = mocks["bq"].create_external_table.call_args_list
    assert [c.kwargs["table_name"] for c in calls] == ["asset_raw_v1_1", "claim_raw_v1_1"]
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


def test_command_skips_stray_folders(ctx_obj: Dict[str, Any], mocks: Dict[str, Any]) -> None:
    mocks["gcs"].list_all_blobs_with_prefix.return_value = [
        "prefix/claim_raw_v1-1/report_date=2023-06-30/a.csv.gz",
        "prefix/claim_raw/report_date=2025-12-31/YouTube_X_M_20251201_claim_raw_v1-1.csv.gz",
        "prefix/video_raw_v1-1/report_date=2025-12-31/b.csv.gz",
    ]

    result = _invoke(ctx_obj)

    assert result.exit_code == 0, result.output
    assert "Skipping 2 folders" in result.output
    assert re.search(r"prefix/claim_raw(?!_)", result.output)
    assert "prefix/video_raw_v1-1" in result.output
    mocks["bq"].create_external_table.assert_called_once_with(
        table_name="claim_raw_v1_1",
        storage_folder_name="prefix/claim_raw_v1-1",
        use_hive_partitioning=True,
    )
