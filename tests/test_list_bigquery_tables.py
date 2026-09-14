"""Tests for list-bigquery-tables command."""

from datetime import datetime
from typing import Any, Dict, cast
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from datawagon.commands.list_bigquery_tables import list_bigquery_tables
from datawagon.objects.app_config import AppConfig
from datawagon.objects.bigquery_table_metadata import BigQueryTableInfo


@pytest.fixture
def ctx_obj() -> Dict[str, Any]:
    app_config = AppConfig(
        csv_source_dir="/tmp",
        csv_source_config="/tmp/config.toml",
        gcs_project_id="project",
        gcs_bucket="bucket",
        bq_dataset="dataset",
    )
    return {"CONFIG": app_config}


def _table(name: str, uri: str, created: datetime | None = None, partitioned: bool = False) -> BigQueryTableInfo:
    return BigQueryTableInfo(
        table_name=name,
        dataset_id="dataset",
        project_id="project",
        source_uri_pattern=uri,
        is_partitioned=partitioned,
        created_time=created,
    )


@patch("datawagon.commands.list_bigquery_tables.BigQueryManager")
def test_connection_error_aborts(mock_bq_class: Any, ctx_obj: Dict[str, Any]) -> None:
    mock_bq_class.return_value = Mock(has_error=True)

    result = CliRunner().invoke(list_bigquery_tables, [], obj=ctx_obj)

    assert result.exit_code == 1
    assert "Unable to connect to BigQuery" in result.output
    mock_bq_class.return_value.list_external_tables.assert_not_called()
    assert "BQ_MANAGER" not in ctx_obj


@patch("datawagon.commands.list_bigquery_tables.BigQueryManager")
def test_no_tables_returns_empty_list(mock_bq_class: Any, ctx_obj: Dict[str, Any]) -> None:
    mock_bq = Mock(has_error=False)
    mock_bq.list_external_tables.return_value = []
    mock_bq_class.return_value = mock_bq

    result = CliRunner().invoke(list_bigquery_tables, [], obj=ctx_obj, standalone_mode=False)

    assert result.exit_code == 0
    assert cast(Any, result).return_value == []
    assert "No external tables found" in result.output
    assert ctx_obj["BQ_MANAGER"] is mock_bq


@patch("datawagon.commands.list_bigquery_tables.BigQueryManager")
def test_uses_config_dataset_by_default(mock_bq_class: Any, ctx_obj: Dict[str, Any]) -> None:
    mock_bq_class.return_value.has_error = False
    mock_bq_class.return_value.list_external_tables.return_value = []

    CliRunner().invoke(list_bigquery_tables, [], obj=ctx_obj)

    mock_bq_class.assert_called_once_with(project_id="project", dataset_id="dataset", bucket_name="bucket")


@patch("datawagon.console.table")
@patch("datawagon.commands.list_bigquery_tables.BigQueryManager")
def test_lists_tables_and_formats_rows(mock_bq_class: Any, mock_table: Any, ctx_obj: Dict[str, Any]) -> None:
    long_uri = "gs://bucket/" + "x" * 80
    tables = [
        _table("claim_raw_v1_1", "gs://bucket/claim/*", created=datetime(2024, 1, 2, 3, 4), partitioned=True),
        _table("asset_raw_v1_1", long_uri),
    ]
    mock_bq = Mock(has_error=False)
    mock_bq.list_external_tables.return_value = tables
    mock_bq_class.return_value = mock_bq

    result = CliRunner().invoke(list_bigquery_tables, ["--dataset", "other_ds"], obj=ctx_obj, standalone_mode=False)

    assert result.exit_code == 0
    assert cast(Any, result).return_value == tables
    assert "Found 2 external tables in dataset 'other_ds'" in result.output
    assert mock_bq_class.call_args.kwargs["dataset_id"] == "other_ds"

    kwargs = mock_table.call_args.kwargs
    assert kwargs["title"] == "External Tables in other_ds"
    assert kwargs["data"] == [
        ["claim_raw_v1_1", "2024-01-02 03:04", "Yes", "gs://bucket/claim/*"],
        ["asset_raw_v1_1", "Unknown", "No", long_uri[:60] + "..."],
    ]
