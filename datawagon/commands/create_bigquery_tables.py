"""Create BigQuery external tables command."""
import re
from collections import defaultdict
from typing import List

import click

from datawagon.bucket.bigquery_manager import BigQueryManager
from datawagon.bucket.gcs_manager import GcsManager
from datawagon.commands.list_bigquery_tables import list_bigquery_tables
from datawagon.console import (
    confirm,
    error,
    info,
    inline_status_end,
    inline_status_start,
    newline,
    success,
    table,
    warning,
)
from datawagon.objects.app_config import AppConfig
from datawagon.objects.bigquery_table_metadata import (
    BigQueryTableInfo,
    StorageFolderSummary,
)


@click.command(name="create-bigquery-tables")
@click.option(
    "--dataset",
    type=click.STRING,
    default=None,
    required=False,
    help="BigQuery dataset name (defaults to DW_BQ_DATASET env var)",
)
@click.pass_context
def create_bigquery_tables(ctx: click.Context, dataset: str | None) -> None:
    """Create BigQuery external tables for GCS folders without tables.

    Workflow:
    1. Scan GCS bucket for storage folders with CSV files
    2. List existing BigQuery external tables
    3. Identify folders without corresponding tables
    4. Show user what will be created
    5. Prompt for confirmation
    6. Create external tables with Hive partitioning
    """
    app_config: AppConfig = ctx.obj["CONFIG"]

    # Use provided dataset or default from config
    dataset_id = dataset or app_config.bq_dataset

    # Initialize managers
    gcs_manager = ctx.obj.get("GCS_MANAGER")
    if not gcs_manager:
        gcs_manager = GcsManager(app_config.gcs_project_id, app_config.gcs_bucket)
        if gcs_manager.has_error:
            error("Unable to connect to GCS. Check credentials and try again.")
            ctx.abort()
        ctx.obj["GCS_MANAGER"] = gcs_manager

    # Get existing BigQuery tables
    existing_tables: List[BigQueryTableInfo] = ctx.invoke(
        list_bigquery_tables, dataset=dataset_id
    )
    existing_table_names = {table.table_name for table in existing_tables}

    bq_manager: BigQueryManager = ctx.obj["BQ_MANAGER"]

    # Scan GCS bucket for storage folders
    info(f"Scanning GCS bucket for folders under '{app_config.bq_storage_prefix}/'...")
    storage_folders = _scan_gcs_storage_folders(
        gcs_manager, app_config.gcs_bucket, storage_prefix=app_config.bq_storage_prefix
    )

    if not storage_folders:
        warning("No storage folders found in GCS bucket.")
        return

    success(f"Found {len(storage_folders)} storage folders in GCS")

    # Identify folders without BigQuery tables
    folders_to_create = []
    for folder in storage_folders:
        if folder.proposed_bq_table_name not in existing_table_names:
            folders_to_create.append(folder)

    if not folders_to_create:
        newline()
        success("All storage folders already have corresponding BigQuery tables.")
        return

    # Display folders that need tables
    newline()
    warning(f"Found {len(folders_to_create)} storage folders without BigQuery tables:")
    newline()

    table_data = []
    for folder in folders_to_create:
        partitioned = "Yes" if folder.has_partitioning else "No"
        table_data.append(
            [
                folder.proposed_bq_table_name,
                folder.storage_folder_name,
                folder.file_count,
                partitioned,
            ]
        )

    table(
        data=table_data,
        headers=["Table to Create", "GCS Folder", "File Count", "Partitioned"],
        title="Tables to Create",
    )
    newline()

    # Prompt for confirmation
    confirm(
        f"Create {len(folders_to_create)} BigQuery external tables?",
        default=False,
        abort=True,
    )

    newline()

    # Create tables
    success_count = 0
    error_count = 0

    for folder in folders_to_create:
        inline_status_start(f"Creating table {folder.proposed_bq_table_name}...")

        success_result = bq_manager.create_external_table(
            table_name=folder.proposed_bq_table_name,
            storage_folder_name=folder.storage_folder_name,
            use_hive_partitioning=folder.has_partitioning,
            partition_column="report_date",
        )

        inline_status_end(success_result)

        if success_result:
            success_count += 1
        else:
            error_count += 1

    # Summary
    newline()
    if error_count > 0:
        warning(f"Created {success_count} tables, {error_count} errors. Check logs.")
    else:
        success(f"Successfully created {success_count} external tables!")


def _scan_gcs_storage_folders(
    gcs_manager: GcsManager, bucket_name: str, storage_prefix: str = ""
) -> List[StorageFolderSummary]:
    """Scan GCS bucket and identify storage folders with CSV files.

    Groups files by storage folder, extracts version information,
    and detects partitioning patterns.

    Args:
        gcs_manager: GCS manager instance
        bucket_name: GCS bucket name
        storage_prefix: Optional prefix to filter folders (e.g., "caravan-versioned")

    Returns:
        List of StorageFolderSummary objects
    """
    # List all CSV.GZ files in bucket under the specified prefix
    all_blobs = gcs_manager.list_all_blobs_with_prefix(prefix=storage_prefix)
    csv_blobs = [blob for blob in all_blobs if blob.endswith(".csv.gz")]

    if not csv_blobs:
        return []

    # Group files by storage folder
    folder_groups = defaultdict(list)
    for blob in csv_blobs:
        # Extract storage folder (first part of path before partition or file)
        # Example: caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/file.csv.gz
        #          → caravan-versioned/claim_raw_v1-1

        parts = blob.split("/")
        if len(parts) >= 2:
            # Check if path includes partition (report_date=*)
            if any("report_date=" in part for part in parts):
                # Take everything before partition directory
                partition_idx = next(
                    i for i, p in enumerate(parts) if "report_date=" in p
                )
                folder_path = "/".join(parts[:partition_idx])
            else:
                # No partitioning, take everything except filename
                folder_path = "/".join(parts[:-1])

            folder_groups[folder_path].append(blob)

    # Create StorageFolderSummary for each folder
    summaries = []
    for folder_path, files in folder_groups.items():
        # Extract table name and version from folder path
        # Example: caravan-versioned/claim_raw_v1-1 → table=claim_raw, version=v1-1
        folder_name = folder_path.split("/")[-1]

        # Try to extract version pattern
        version_match = re.search(r"_v\d+(-\d+)?$", folder_name)
        if version_match:
            file_version = version_match.group(0).lstrip("_")  # v1-1
            table_name = folder_name[: version_match.start()]  # claim_raw
        else:
            file_version = ""
            table_name = folder_name

        # Normalize table name for BigQuery (replace hyphens in version)
        proposed_bq_table_name = BigQueryManager.normalize_table_name(
            table_name, file_version
        )

        # Check if files use partitioning
        has_partitioning = any("report_date=" in file for file in files)

        # Sample files for display
        sample_files = files[:3]

        summary = StorageFolderSummary(
            storage_folder_name=folder_path,
            table_name=table_name,
            file_version=file_version,
            proposed_bq_table_name=proposed_bq_table_name,
            file_count=len(files),
            has_partitioning=has_partitioning,
            sample_files=sample_files,
        )
        summaries.append(summary)

    # Sort by table name for consistent display
    summaries.sort(key=lambda x: x.proposed_bq_table_name)

    return summaries
