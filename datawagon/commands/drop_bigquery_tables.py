"""Drop BigQuery external tables command."""
from typing import List

import click
from tabulate import tabulate

from datawagon.bucket.bigquery_manager import BigQueryManager
from datawagon.commands.list_bigquery_tables import list_bigquery_tables
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
        click.secho("No external tables found in dataset.", fg="yellow")
        return

    bq_manager: BigQueryManager = ctx.obj["BQ_MANAGER"]

    # Filter to tables to drop
    if table_name:
        # Drop specific table
        tables_to_drop = [t for t in existing_tables if t.table_name == table_name]
        if not tables_to_drop:
            click.secho(f"Table '{table_name}' not found in dataset.", fg="red")
            return
    else:
        # Drop all tables
        tables_to_drop = existing_tables

    # Display tables to be dropped
    click.echo(nl=True)
    click.secho(
        f"Tables to drop in dataset '{dataset_id}':",
        fg="yellow",
        bold=True,
    )
    click.echo(nl=True)

    table_data = []
    for table in tables_to_drop:
        partitioned = "Yes" if table.is_partitioned else "No"
        created_str = (
            table.created_time.strftime("%Y-%m-%d %H:%M")
            if table.created_time
            else "Unknown"
        )
        table_data.append(
            [
                table.table_name,
                created_str,
                partitioned,
                table.source_uri_pattern[:50] + "..."
                if len(table.source_uri_pattern) > 50
                else table.source_uri_pattern,
            ]
        )

    click.echo(
        tabulate(
            table_data,
            headers=["Table Name", "Created", "Partitioned", "Source URI Pattern"],
            tablefmt="simple",
        )
    )
    click.echo(nl=True)

    # Dry-run mode
    if dry_run:
        click.secho(
            f"DRY-RUN MODE: Would drop {len(tables_to_drop)} table(s).",
            fg="yellow",
            bold=True,
        )
        click.echo("Run with --execute to actually delete these tables.")
        click.echo(nl=True)
        click.secho(
            "⚠️  Note: Only table metadata is deleted. CSV files in GCS remain untouched.",
            fg="cyan",
        )
        return

    # Execute mode - require confirmation
    click.secho(
        "⚠️  WARNING: This will permanently delete table metadata!",
        fg="red",
        bold=True,
    )
    click.echo("The underlying CSV files in GCS will NOT be deleted.")
    click.echo(nl=True)

    try:
        click.confirm(
            f"Are you sure you want to drop {len(tables_to_drop)} table(s)?",
            default=False,
            abort=True,
        )
    except click.Abort:
        click.echo("Aborted.")
        return

    # Drop tables
    click.echo(nl=True)
    success_count = 0
    error_count = 0

    for table in tables_to_drop:
        click.echo(f"Dropping table {table.table_name}... ", nl=False)

        success = bq_manager.delete_table(table.table_name)

        if success:
            success_count += 1
            click.secho("Success", fg="green")
        else:
            error_count += 1
            click.secho("Failed", fg="red")

    # Summary
    click.echo(nl=True)
    if error_count > 0:
        click.secho(
            f"Dropped {success_count} table(s), {error_count} error(s). Check logs.",
            fg="yellow",
            bold=True,
        )
    else:
        click.secho(
            f"Successfully dropped {success_count} table(s)!",
            fg="green",
            bold=True,
        )
