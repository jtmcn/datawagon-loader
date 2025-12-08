"""DataWagon CLI application entry point.

This module provides the main Click CLI interface for DataWagon, which automates
loading CSV files from local filesystem to Google Cloud Storage buckets. It handles
configuration loading, validation, logging setup, and command orchestration.

The CLI supports command chaining, allowing multiple operations to be executed in
sequence (e.g., `datawagon files-in-local-fs compare-local-to-bucket upload-to-gcs`).
"""
import importlib.metadata
from pathlib import Path

import click
import toml
from dotenv import find_dotenv, load_dotenv
from pydantic import ValidationError

from datawagon.commands.compare import compare_local_files_to_bucket
from datawagon.commands.create_bigquery_tables import create_bigquery_tables
from datawagon.commands.drop_bigquery_tables import drop_bigquery_tables
from datawagon.commands.file_zip_to_gzip import file_zip_to_gzip
from datawagon.commands.files_in_local_fs import files_in_local_fs
from datawagon.commands.files_in_storage import files_in_storage
from datawagon.commands.list_bigquery_tables import list_bigquery_tables
from datawagon.commands.migrate_to_versioned_folders import migrate_to_versioned_folders
from datawagon.commands.upload_to_storage import upload_all_gzip_csv
from datawagon.logging_config import setup_logging
from datawagon.objects.app_config import AppConfig
from datawagon.objects.source_config import SourceConfig


@click.group(chain=True)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging (DEBUG level)",
)
@click.option(
    "--log-file",
    type=click.Path(),
    help="Write logs to file",
)
@click.option(
    "--csv-source-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    help="Source directory containing .csv, .csv.zip or .csv.gz files.",
    envvar="DW_CSV_SOURCE_DIR",
)
@click.option(
    "--csv-source-config",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    help="Location of source_config.toml",
    envvar="DW_CSV_SOURCE_TOML",
)
@click.option(
    "--gcs-project-id",
    type=str,
    help="Project ID for Google Cloud Storage",
    envvar="DW_GCS_PROJECT_ID",
)
@click.option(
    "--gcs-bucket",
    type=str,
    help="Bucket used for Google Cloud Storage",
    envvar="DW_GCS_BUCKET",
)
@click.option(
    "--bq-dataset",
    type=str,
    help="BigQuery dataset for external tables",
    envvar="DW_BQ_DATASET",
)
@click.option(
    "--bq-storage-prefix",
    type=str,
    default="caravan-versioned",
    help="GCS folder prefix for BigQuery table creation (default: caravan-versioned)",
    envvar="DW_BQ_STORAGE_PREFIX",
)
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    log_file: str,
    csv_source_dir: Path,
    csv_source_config: Path,
    gcs_project_id: str,
    gcs_bucket: str,
    bq_dataset: str,
    bq_storage_prefix: str,
) -> None:
    """DataWagon CLI group for processing CSV files to Google Cloud Storage.

    This is the main CLI entry point that handles configuration loading, validation,
    and context setup for all commands. Supports command chaining for sequential
    operations.

    Args:
        ctx: Click context object for passing data between commands
        verbose: Enable DEBUG level logging if True
        log_file: Optional path to write log output
        csv_source_dir: Directory containing CSV files to process
        csv_source_config: Path to source_config.toml configuration file
        gcs_project_id: Google Cloud Platform project ID
        gcs_bucket: GCS bucket name for uploads
        bq_dataset: BigQuery dataset for external tables
        bq_storage_prefix: GCS folder prefix for BigQuery table creation

    Raises:
        click.UsageError: If required parameters are missing or invalid
        ValueError: If source_config.toml fails Pydantic validation

    Example:
        >>> datawagon files-in-local-fs compare-local-to-bucket upload-to-gcs
    """
    # Setup logging
    logger = setup_logging(verbose=verbose, log_file=log_file)
    ctx.ensure_object(dict)
    ctx.obj["logger"] = logger

    # Validate CLI parameters
    import os

    if not csv_source_dir or not os.path.exists(csv_source_dir):
        raise click.UsageError(f"CSV source directory does not exist: {csv_source_dir}")
    if not csv_source_config or not os.path.exists(csv_source_config):
        raise click.UsageError(f"Source config TOML not found: {csv_source_config}")
    if not gcs_project_id:
        raise click.UsageError("GCS_PROJECT_ID must be set")
    if not gcs_bucket:
        raise click.UsageError("GCS_BUCKET must be set")
    if not bq_dataset:
        raise click.UsageError("BQ_DATASET must be set")

    logger.info(f"csv_source_config: {csv_source_config}")

    try:
        source_config_file = toml.load(csv_source_config)
        valid_config = SourceConfig(**source_config_file)

    except ValidationError as e:
        raise ValueError(f"Validation Failed for source_config.toml\n{e}")

    if not valid_config:
        ctx.abort()

    ctx.obj["FILE_CONFIG"] = valid_config

    app_config = AppConfig(
        csv_source_dir=csv_source_dir,
        csv_source_config=csv_source_config,
        gcs_project_id=gcs_project_id,
        gcs_bucket=gcs_bucket,
        bq_dataset=bq_dataset,
        bq_storage_prefix=bq_storage_prefix,
    )

    ctx.obj["CONFIG"] = app_config
    ctx.obj["GLOBAL"] = {}


cli.add_command(files_in_local_fs)
cli.add_command(compare_local_files_to_bucket)
cli.add_command(upload_all_gzip_csv)
cli.add_command(file_zip_to_gzip)
cli.add_command(files_in_storage)
cli.add_command(list_bigquery_tables)
cli.add_command(create_bigquery_tables)
cli.add_command(drop_bigquery_tables)
cli.add_command(migrate_to_versioned_folders)


def start_cli() -> click.Group:
    """Initialize and start the DataWagon CLI application.

    Loads environment variables from .env file, displays application banner with
    version information, and initializes the Click CLI group.

    Returns:
        The initialized Click CLI group object

    Raises:
        FileNotFoundError: If .env file is not found in current or parent directories

    Example:
        >>> start_cli()
        DataWagon
        Version: 1.0.0
        Configuration loaded from: /path/to/.env
    """
    env_file = find_dotenv(usecwd=True, raise_error_if_not_found=True)

    load_dotenv(env_file, verbose=True)

    click.secho("DataWagon", fg="magenta", bold=True)
    click.echo(f"Version: {importlib.metadata.version('datawagon')}")
    click.secho(f"Configuration loaded from: {env_file}")
    click.echo(nl=True)

    return cli(obj={})  # type: ignore


if __name__ == "__main__":
    start_cli()
