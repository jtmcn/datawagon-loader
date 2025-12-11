"""Tests for BigQuery table metadata models."""
from datetime import datetime

from datawagon.objects.bigquery_table_metadata import (
    BigQueryTableInfo,
    StorageFolderSummary,
)


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


def test_storage_folder_summary_creation() -> None:
    """Test creating StorageFolderSummary."""
    folder = StorageFolderSummary(
        storage_folder_name="caravan-versioned/claim_raw_v1-1",
        table_name="claim_raw",
        file_version="v1-1",
        proposed_bq_table_name="claim_raw_v1_1",
        file_count=120,
        has_partitioning=True,
        sample_files=[
            "caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/file1.csv.gz"
        ],
    )

    assert folder.storage_folder_name == "caravan-versioned/claim_raw_v1-1"
    assert folder.table_name == "claim_raw"
    assert folder.file_version == "v1-1"
    assert folder.proposed_bq_table_name == "claim_raw_v1_1"
    assert folder.file_count == 120
    assert folder.has_partitioning is True
    assert len(folder.sample_files) == 1


def test_storage_folder_summary_without_version() -> None:
    """Test creating StorageFolderSummary without version."""
    folder = StorageFolderSummary(
        storage_folder_name="simple-folder",
        table_name="simple_table",
        file_version="",
        proposed_bq_table_name="simple_table",
        file_count=50,
        has_partitioning=False,
    )

    assert folder.file_version == ""
    assert folder.proposed_bq_table_name == "simple_table"
    assert folder.has_partitioning is False
    assert folder.sample_files == []


def test_storage_folder_summary_default_sample_files() -> None:
    """Test StorageFolderSummary with default empty sample_files."""
    folder = StorageFolderSummary(
        storage_folder_name="test-folder",
        table_name="test_table",
        file_version="v1",
        proposed_bq_table_name="test_table_v1",
        file_count=10,
        has_partitioning=True,
    )

    assert folder.sample_files == []
