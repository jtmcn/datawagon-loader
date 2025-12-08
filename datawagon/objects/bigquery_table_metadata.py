"""BigQuery table metadata models.

This module defines Pydantic models for tracking BigQuery external table
metadata, including source URIs, partitioning configuration, and creation info.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BigQueryTableInfo(BaseModel):
    """Metadata for a BigQuery external table.

    Attributes:
        table_name: Name of the BigQuery table (with version: claim_raw_v1_1)
        dataset_id: BigQuery dataset containing the table
        project_id: GCP project ID
        source_uri_pattern: GCS URI pattern (gs://bucket/folder/report_date=*/*.csv.gz)
        storage_folder_name: GCS folder name (caravan-versioned/claim_raw_v1-1)
        is_partitioned: Whether table uses Hive partitioning
        partition_columns: List of partition column names (e.g., ["report_date"])
        created_time: When table was created
        num_rows: Number of rows (always None for external tables)

    Example:
        >>> table_info = BigQueryTableInfo(
        ...     table_name="claim_raw_v1_1",
        ...     dataset_id="youtube_analytics_raw",
        ...     project_id="my-project",
        ...     source_uri_pattern="gs://bucket/caravan-versioned/claim_raw_v1-1/report_date=*/*.csv.gz",
        ...     storage_folder_name="caravan-versioned/claim_raw_v1-1",
        ...     is_partitioned=True,
        ...     partition_columns=["report_date"]
        ... )
    """

    table_name: str
    dataset_id: str
    project_id: str
    source_uri_pattern: str
    storage_folder_name: Optional[str] = None
    is_partitioned: bool = False
    partition_columns: Optional[list[str]] = None
    created_time: Optional[datetime] = None
    num_rows: Optional[int] = None

    @property
    def full_table_id(self) -> str:
        """Return fully qualified table ID."""
        return f"{self.project_id}.{self.dataset_id}.{self.table_name}"


class StorageFolderSummary(BaseModel):
    """Summary of files in a GCS storage folder.

    Attributes:
        storage_folder_name: Name of the storage folder (e.g., caravan-versioned/claim_raw_v1-1)
        table_name: Base table name without version (e.g., claim_raw)
        file_version: File version string (e.g., v1-1)
        proposed_bq_table_name: Suggested BigQuery table name (e.g., claim_raw_v1_1)
        file_count: Number of CSV files in this folder
        has_partitioning: Whether files use report_date partitioning
        sample_files: List of 3-5 sample file paths

    Example:
        >>> folder = StorageFolderSummary(
        ...     storage_folder_name="caravan-versioned/claim_raw_v1-1",
        ...     table_name="claim_raw",
        ...     file_version="v1-1",
        ...     proposed_bq_table_name="claim_raw_v1_1",
        ...     file_count=120,
        ...     has_partitioning=True,
        ...     sample_files=["caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/file1.csv.gz"]
        ... )
    """

    storage_folder_name: str
    table_name: str
    file_version: str
    proposed_bq_table_name: str
    file_count: int
    has_partitioning: bool
    sample_files: list[str] = Field(default_factory=list)
