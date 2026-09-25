"""Tests for BigQuery table metadata models."""

from datetime import datetime

from datawagon.objects.bigquery_table_metadata import BigQueryTableInfo


def test_bigquery_table_info_creation() -> None:
    """Test creating BigQueryTableInfo with all fields."""
    table_info = BigQueryTableInfo(
        table_name="claim_raw_v1_1",
        dataset_id="youtube_analytics_raw",
        project_id="my-project",
        source_uri_pattern="gs://bucket/folder/report_date=*/*.csv.gz",
        storage_folder_name="caravan-versioned/claim_raw_v1-1",
        is_partitioned=True,
        partition_columns=["report_date"],
        created_time=datetime(2024, 1, 1, 12, 0, 0),
        num_rows=None,
    )

    assert table_info.table_name == "claim_raw_v1_1"
    assert table_info.dataset_id == "youtube_analytics_raw"
    assert table_info.project_id == "my-project"
    assert table_info.is_partitioned is True
    assert table_info.partition_columns == ["report_date"]


def test_bigquery_table_info_full_table_id() -> None:
    """Test full_table_id property."""
    table_info = BigQueryTableInfo(
        table_name="claim_raw_v1_1",
        dataset_id="youtube_analytics_raw",
        project_id="my-project",
        source_uri_pattern="gs://bucket/folder/report_date=*/*.csv.gz",
    )

    assert table_info.full_table_id == "my-project.youtube_analytics_raw.claim_raw_v1_1"


def test_bigquery_table_info_minimal() -> None:
    """Test creating BigQueryTableInfo with minimal fields."""
    table_info = BigQueryTableInfo(
        table_name="simple_table",
        dataset_id="dataset",
        project_id="project",
        source_uri_pattern="gs://bucket/folder/*.csv.gz",
    )

    assert table_info.table_name == "simple_table"
    assert table_info.is_partitioned is False
    assert table_info.partition_columns is None
    assert table_info.storage_folder_name is None
