"""BigQuery table metadata models.

This module defines Pydantic models for tracking BigQuery external table
metadata, including source URIs, partitioning configuration, and creation info.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
