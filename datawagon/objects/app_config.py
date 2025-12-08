"""Application configuration model.

This module defines the runtime configuration for DataWagon, storing paths and
GCS credentials needed for CSV file processing and uploads.
"""
from pathlib import Path

from pydantic import BaseModel


class AppConfig(BaseModel):
    """Application runtime configuration.

    Stores essential runtime parameters for DataWagon including file paths
    and Google Cloud Storage credentials. Validated using Pydantic.

    Attributes:
        csv_source_dir: Path to directory containing CSV files to process
        csv_source_config: Path to source_config.toml configuration file
        gcs_project_id: Google Cloud Platform project ID for GCS access
        gcs_bucket: GCS bucket name where files will be uploaded
        bq_dataset: BigQuery dataset name for external tables

    Example:
        >>> config = AppConfig(
        ...     csv_source_dir=Path("/data/csv"),
        ...     csv_source_config=Path("/config/source.toml"),
        ...     gcs_project_id="my-project",
        ...     gcs_bucket="my-bucket",
        ...     bq_dataset="my_dataset"
        ... )
    """

    csv_source_dir: Path
    csv_source_config: Path
    gcs_project_id: str
    gcs_bucket: str
    bq_dataset: str
