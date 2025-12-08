"""Drop BigQuery external tables command."""
from typing import List

import click

from datawagon.bucket.bigquery_manager import BigQueryManager
from datawagon.commands.list_bigquery_tables import list_bigquery_tables
from datawagon.console import (
    confirm,
    error,
    info,
    inline_status_end,
    inline_status_start,
    newline,
    panel,
    success,
    table,
    warning,
)
from datawagon.objects.app_config import AppConfig
from datawagon.objects.bigquery_table_metadata import BigQueryTableInfo


@click.command(name="drop-bigquery-tables")
@click.option(
    "--dry-run/--execute",
    default=True,
    help="Show tables to drop without executing (default: dry-run)",
)
@click.option(
    "--table-name",
    type=click.STRING,
    default=None,
    required=False,
    help="Drop specific table by name. If not specified, drops all tables.",
)
@click.option(
    "--dataset",
    type=click.STRING,
    default=None,
    required=False,
    help="BigQuery dataset name (defaults to DW_BQ_DATASET env var)",
)
@click.pass_context
def drop_bigquery_tables(
    ctx: click.Context, dry_run: bool, table_name: str | None, dataset: str | None
) -> None:
    """Drop BigQuery external tables.

    By default, this command runs in DRY-RUN mode and shows what would be deleted
    without making any changes. Use --execute to actually delete tables.

    Safety Features:
    - Dry-run mode by default (must explicitly use --execute)
    - Shows preview of tables to be dropped
    - Requires explicit user confirmation before deletion
    - Only deletes table metadata (CSV files in GCS remain untouched)

    Examples:
        # Show what would be deleted (dry-run)
        datawagon drop-bigquery-tables

        # Drop all tables (with confirmation)
        datawagon drop-bigquery-tables --execute

        # Drop specific table
        datawagon drop-bigquery-tables --execute --table-name claim_raw_v1_1

        # Drop from specific dataset
        datawagon drop-bigquery-tables --execute --dataset my_dataset
    """
    app_config: AppConfig = ctx.obj["CONFIG"]

    # Use provided dataset or default from config
    dataset_id = dataset or app_config.bq_dataset

    # Get existing BigQuery tables
    existing_tables: List[BigQueryTableInfo] = ctx.invoke(
        list_bigquery_tables, dataset=dataset_id
    )

    if not existing_tables:
        warning("No external tables found in dataset.")
        return

    bq_manager: BigQueryManager = ctx.obj["BQ_MANAGER"]

    # Filter to tables to drop
    if table_name:
        # Drop specific table
        tables_to_drop = [t for t in existing_tables if t.table_name == table_name]
        if not tables_to_drop:
            error(f"Table '{table_name}' not found in dataset.")
            return
    else:
        # Drop all tables
        tables_to_drop = existing_tables

    # Display tables to be dropped
    newline()
    warning(f"Tables to drop in dataset '{dataset_id}':")
    newline()

    table_data = []
    for tbl in tables_to_drop:
        partitioned = "Yes" if tbl.is_partitioned else "No"
        created_str = (
            tbl.created_time.strftime("%Y-%m-%d %H:%M")
            if tbl.created_time
            else "Unknown"
        )
        table_data.append(
            [
                tbl.table_name,
                created_str,
                partitioned,
                tbl.source_uri_pattern[:50] + "..."
                if len(tbl.source_uri_pattern) > 50
                else tbl.source_uri_pattern,
            ]
        )

    table(
        data=table_data,
        headers=["Table Name", "Created", "Partitioned", "Source URI Pattern"],
        title=f"Tables to Drop from {dataset_id}",
    )
    newline()

    # Dry-run mode
    if dry_run:
        panel(
            f"DRY-RUN MODE: Would drop {len(tables_to_drop)} table(s).\n\n"
            f"Run with --execute to actually delete these tables.\n\n"
            f"⚠️  Note: Only table metadata is deleted. CSV files in GCS remain untouched.",
            title="Dry Run",
            style="yellow",
            border_style="yellow",
        )
        return

    # Execute mode - require confirmation
    error("⚠️  WARNING: This will permanently delete table metadata!")
    info("The underlying CSV files in GCS will NOT be deleted.")
    newline()

    try:
        confirm(
            f"Are you sure you want to drop {len(tables_to_drop)} table(s)?",
            default=False,
            abort=True,
        )
    except click.Abort:
        info("Aborted.")
        return

    # Drop tables
    newline()
    success_count = 0
    error_count = 0

    for tbl in tables_to_drop:
        inline_status_start(f"Dropping table {tbl.table_name}...")

        success_result = bq_manager.delete_table(tbl.table_name)

        inline_status_end(success_result)

        if success_result:
            success_count += 1
        else:
            error_count += 1

    # Summary
    newline()
    if error_count > 0:
        warning(f"Dropped {success_count} table(s), {error_count} error(s). Check logs.")
    else:
        success(f"Successfully dropped {success_count} table(s)!")
