"""Recreate BigQuery external tables with lowercase column names."""

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
from datawagon.objects.bigquery_table_metadata import BigQueryTableInfo


@click.command(name="recreate-bigquery-tables")
@click.option(
    "--dataset",
    type=click.STRING,
    default=None,
    required=False,
    help="BigQuery dataset name (defaults to DW_BQ_DATASET env var)",
)
@click.option(
    "--tables",
    type=click.STRING,
    default=None,
    required=False,
    help="Comma-separated list of table names to recreate (default: all)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt (use with caution)",
)
@click.pass_context
def recreate_bigquery_tables(
    ctx: click.Context,
    dataset: str | None,
    tables: str | None,
    force: bool,
) -> None:
    """Recreate BigQuery external tables with lowercase column names.

    WARNING: This command will DROP and RECREATE tables. External tables
    don't contain data (they reference GCS files), but any views or queries
    using these tables may break if they reference old column names.

    Workflow:
    1. List existing BigQuery external tables
    2. Infer new schemas with lowercase column names from GCS files
    3. Show user what will be recreated
    4. Prompt for confirmation (unless --force)
    5. Drop existing tables
    6. Recreate with new lowercase schemas
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

    if not existing_tables:
        warning("No external tables found to recreate.")
        return

    # Filter to specific tables if requested
    if tables:
        table_names = {t.strip() for t in tables.split(",")}
        existing_tables = [t for t in existing_tables if t.table_name in table_names]

        if not existing_tables:
            error(f"No matching tables found: {tables}")
            return

    # Initialize BigQuery manager
    bq_manager = ctx.obj.get("BQ_MANAGER")
    if not bq_manager:
        bq_manager = BigQueryManager(app_config.gcs_project_id, dataset_id, app_config.gcs_bucket)
        if bq_manager.has_error:
            error("Failed to connect to BigQuery. Check credentials.")
            ctx.abort()
        ctx.obj["BQ_MANAGER"] = bq_manager

    # Display warning
    newline()
    warning(f"WARNING: This will DROP and RECREATE {len(existing_tables)} tables!")
    info("External tables don't contain data, but queries/views may break.")
    newline()

    # Show tables to recreate
    table_data = []
    for tbl in existing_tables:
        partitioned = "Yes" if tbl.is_partitioned else "No"
        source_display = (
            tbl.source_uri_pattern[:60] + "..." if len(tbl.source_uri_pattern) > 60 else tbl.source_uri_pattern
        )
        table_data.append([tbl.table_name, partitioned, source_display])

    table(
        data=table_data,
        headers=["Table Name", "Partitioned", "Source URI"],
        title="Tables to Recreate",
    )
    newline()

    # Confirm unless --force
    if not force:
        confirm(
            f"Drop and recreate {len(existing_tables)} tables with lowercase columns?",
            default=False,
            abort=True,
        )
        newline()

    # Recreate tables
    success_count = 0
    error_count = 0

    for tbl in existing_tables:
        inline_status_start(f"Recreating {tbl.table_name}...")

        # Extract storage folder from source URI
        # gs://bucket/folder/report_date=*/*.csv.gz → folder
        # gs://bucket/folder/* → folder
        source_uri = tbl.source_uri_pattern
        storage_folder = source_uri.replace(f"gs://{app_config.gcs_bucket}/", "")

        # Remove partition suffix if present
        if "/report_date=" in storage_folder:
            storage_folder = storage_folder.split("/report_date=")[0]

        # Remove wildcard suffix
        storage_folder = storage_folder.rstrip("/*")

        # Drop existing table
        if not bq_manager.delete_table(tbl.table_name):
            inline_status_end(False)
            error_count += 1
            continue

        # Recreate with new schema (schema will be inferred automatically)
        recreate_success = bq_manager.create_external_table(
            table_name=tbl.table_name,
            storage_folder_name=storage_folder,
            use_hive_partitioning=tbl.is_partitioned,
            partition_column="report_date",
        )

        inline_status_end(recreate_success)

        if recreate_success:
            success_count += 1
        else:
            error_count += 1

    # Summary
    newline()
    if error_count > 0:
        warning(f"Recreated {success_count} tables, {error_count} errors. Check logs.")
    else:
        success(f"Successfully recreated {success_count} tables with lowercase columns!")
