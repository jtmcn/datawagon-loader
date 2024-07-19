import importlib.metadata
from pathlib import Path

import click
import toml
from dotenv import find_dotenv, load_dotenv
from hologram import ValidationError

from datawagon.commands.compare import compare_local_files_to_bucket
from datawagon.commands.file_zip_to_gzip import file_zip_to_gzip
from datawagon.commands.files_in_local_fs import files_in_local_fs
from datawagon.commands.files_in_storage import files_in_storage
from datawagon.commands.upload_to_storage import upload_all_gzip_csv
from datawagon.objects.app_config import AppConfig
from datawagon.objects.source_config import SourceConfig


@click.group(chain=True)
@click.option("--db-url", type=str, help="Database URL", envvar="DW_POSTGRES_DB_URL")
@click.option("--db-schema", type=str, help="Schema name to use", envvar="DW_DB_SCHEMA")
@click.option(
    "--csv-source-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    help="Source directory containing .csv, .csv.zip or .csv.gz files.",
    envvar="DW_CSV_SOURCE_DIR",
)
@click.option(
    "--csv-source-config",
    type=str,
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
@click.pass_context
def cli(
    ctx: click.Context,
    db_url: str,
    db_schema: str,
    csv_source_dir: Path,
    csv_source_config: Path,
    gcs_project_id: str,
    gcs_bucket: str,
) -> None:
    # if not ParameterValidator(
    #     db_url, db_schema, csv_source_dir, csv_source_config
    # ).are_valid_parameters:
    #     ctx.abort()

    # TODO: fix error handling, this is not working
    # load config from toml file
    try:
        source_config_file = toml.load(csv_source_config)
        valid_config = SourceConfig(**source_config_file)

    except ValidationError as e:
        raise ValueError(f"Validation Failed for source_config.toml\n{e}")

    if not valid_config:
        ctx.abort()

    ctx.obj["FILE_CONFIG"] = valid_config

    app_config = AppConfig(
        db_schema=db_schema,
        csv_source_dir=csv_source_dir,
        csv_source_config=csv_source_config,
        db_url=db_url,
        gcs_project_id=gcs_project_id,
        gcs_bucket=gcs_bucket,
    )

    ctx.obj["CONFIG"] = app_config
    ctx.obj["GLOBAL"] = {}

    # def on_exit() -> None:
    #     if proc:
    #         proc.send_signal(signal.SIGTERM)

    # ctx.call_on_close(on_exit)


cli.add_command(files_in_local_fs)
cli.add_command(compare_local_files_to_bucket)
cli.add_command(upload_all_gzip_csv)
cli.add_command(file_zip_to_gzip)
cli.add_command(files_in_storage)


def start_cli() -> click.Group:
    env_file = find_dotenv()

    load_dotenv(env_file)

    click.secho("DataWagon", fg="magenta", bold=True)
    click.echo(f"Version: {importlib.metadata.version('datawagon')}")
    click.secho(f"Configuration loaded from: {env_file}")
    click.echo(nl=True)

    return cli(obj={})  # type: ignore


if __name__ == "__main__":
    start_cli()
