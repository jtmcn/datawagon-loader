"""Create BigQuery external tables command."""

from collections import defaultdict
from typing import Dict, List, Set, Tuple

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
from datawagon.objects.bigquery_table_metadata import BigQueryTableInfo
from datawagon.objects.storage_layout import StorageLayout, Stray, Table


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
    existing_tables: List[BigQueryTableInfo] = ctx.invoke(list_bigquery_tables, dataset=dataset_id)
    existing_table_names = {table.table_name for table in existing_tables}

    # FIX: Lazy initialization with error handling
    bq_manager = ctx.obj.get("BQ_MANAGER")
    if not bq_manager:
        bq_manager = BigQueryManager(app_config.gcs_project_id, dataset_id, app_config.gcs_bucket)
        if bq_manager.has_error:
            error("Failed to connect to BigQuery. Check credentials and project settings.")
            ctx.abort()
        ctx.obj["BQ_MANAGER"] = bq_manager

    layout: StorageLayout = ctx.obj["STORAGE_LAYOUT"]
    info(f"Scanning GCS bucket for folders under '{layout.prefix}/'...")
    tables, strays = _tables_in_bucket(gcs_manager, layout)

    if strays:
        warning(f"Skipping {len(strays)} folders that no Table can read:")
        for folder in sorted(strays):
            warning(f"  {folder}")

    if not tables:
        warning("No storage folders found in GCS bucket.")
        return

    success(f"Found {len(tables)} storage folders in GCS")

    tables_to_create = {t: count for t, count in tables.items() if t.name not in existing_table_names}

    if not tables_to_create:
        newline()
        success("All storage folders already have corresponding BigQuery tables.")
        return

    # Display folders that need tables
    newline()
    warning(f"Found {len(tables_to_create)} storage folders without BigQuery tables:")
    newline()

    table(
        data=[[t.name, t.folder, count] for t, count in tables_to_create.items()],
        headers=["Table to Create", "GCS Folder", "File Count"],
        title="Tables to Create",
    )
    newline()

    # Prompt for confirmation
    confirm(
        f"Create {len(tables_to_create)} BigQuery external tables?",
        default=False,
        abort=True,
    )

    newline()

    # Create tables
    success_count = 0
    error_count = 0

    for tbl in tables_to_create:
        inline_status_start(f"Creating table {tbl.name}...")

        success_result = bq_manager.create_external_table(
            table_name=tbl.name,
            storage_folder_name=tbl.folder,
            use_hive_partitioning=True,
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


def _tables_in_bucket(gcs_manager: GcsManager, layout: StorageLayout) -> Tuple[Dict[Table, int], Set[str]]:
    """File count per Table found under the Storage Prefix, plus folders that no Table can read."""
    tables: Dict[Table, int] = defaultdict(int)
    strays: Set[str] = set()
    for blob in gcs_manager.list_all_blobs_with_prefix(prefix=layout.prefix):
        if not blob.endswith(".csv.gz"):
            continue
        location = layout.locate(blob)
        if isinstance(location, Stray):
            strays.add(location.folder)
        else:
            tables[layout.table(location.report_type, location.version)] += 1
    return dict(sorted(tables.items())), strays
