"""List BigQuery external tables command."""

from typing import List

import click

from datawagon.bucket.bigquery_manager import BigQueryManager
from datawagon.console import error, newline, success, warning
from datawagon.objects.app_config import AppConfig
from datawagon.objects.bigquery_table_metadata import BigQueryTableInfo


@click.command(name="list-bigquery-tables")
@click.option(
    "--dataset",
    type=click.STRING,
    default=None,
    required=False,
    help="BigQuery dataset name (defaults to DW_BQ_DATASET env var)",
)
@click.pass_context
def list_bigquery_tables(
    ctx: click.Context, dataset: str | None
) -> List[BigQueryTableInfo]:
    """List existing external tables in BigQuery dataset.

    Displays:
    - Table name
    - Creation time
    - Partitioning status
    - Source URI pattern

    Returns:
        List of BigQueryTableInfo objects
    """
    app_config: AppConfig = ctx.obj["CONFIG"]

    # Use provided dataset or default from config
    dataset_id = dataset or app_config.bq_dataset

    # Initialize BigQuery manager
    bq_manager = BigQueryManager(
        project_id=app_config.gcs_project_id,
        dataset_id=dataset_id,
        bucket_name=app_config.gcs_bucket,
    )

    if bq_manager.has_error:
        error("Unable to connect to BigQuery. Check credentials and dataset.")
        ctx.abort()

    # Store manager in context for other commands
    ctx.obj["BQ_MANAGER"] = bq_manager

    # List external tables
    tables = bq_manager.list_external_tables()

    if not tables:
        newline()
        warning("No external tables found in dataset.")
        return []

    # Prepare display data
    table_data = []
    for table in tables:
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
                (
                    table.source_uri_pattern[:60] + "..."
                    if len(table.source_uri_pattern) > 60
                    else table.source_uri_pattern
                ),
            ]
        )

    # Display table
    from datawagon.console import table

    newline()
    success(f"Found {len(tables)} external tables in dataset '{dataset_id}':")
    newline()
    table(
        data=table_data,
        headers=["Table Name", "Created", "Partitioned", "Source URI Pattern"],
        title=f"External Tables in {dataset_id}",
    )
    newline()

    return tables
