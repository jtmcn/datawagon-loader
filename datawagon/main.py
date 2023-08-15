import importlib.metadata
import signal
import subprocess
import sys
from pathlib import Path

import click
from dotenv import find_dotenv, load_dotenv

from datawagon.commands.compare import compare_files_to_database
from datawagon.commands.files_in_database import files_in_database
from datawagon.commands.import_all_csv import import_all_csv
from datawagon.commands.import_single_csv import import_selected_csv
from datawagon.commands.reset_database import reset_database
from datawagon.commands.scan_files import scan_files
from datawagon.objects.app_config import AppConfig
from datawagon.objects.parameter_validator import ParameterValidator
from datawagon.objects.postgres_database_manager import PostgresDatabaseManager


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
@click.pass_context
def cli(
    ctx: click.Context,
    db_url: str,
    db_schema: str,
    csv_source_dir: Path,
    csv_source_config: Path,
) -> None:
    if not ParameterValidator(
        db_url, db_schema, csv_source_dir, csv_source_config
    ).are_valid_parameters:
        ctx.abort()

    app_config = AppConfig(
        db_schema=db_schema,
        csv_source_dir=csv_source_dir,
        csv_source_config=csv_source_config,
        db_url=db_url,
    )

    db_manager = PostgresDatabaseManager(app_config)

    # if on mac, prevent computer from sleeping (display, system, disk)
    if "darwin" in sys.platform:
        proc = subprocess.Popen(["caffeinate", "-dim"])

    ctx.obj["DB_CONNECTION"] = db_manager
    check_db_connection(ctx=ctx, db_manager=db_manager)
    check_schema(ctx=ctx, db_manager=db_manager, schema_name=db_schema)
    db_manager.create_log_table()

    ctx.obj["CONFIG"] = app_config
    ctx.obj["GLOBAL"] = {}

    def on_exit() -> None:
        db_manager.close()
        if proc:
            proc.send_signal(signal.SIGTERM)

    ctx.call_on_close(on_exit)


cli.add_command(reset_database)
cli.add_command(files_in_database)
cli.add_command(scan_files)
cli.add_command(compare_files_to_database)
cli.add_command(import_all_csv)
cli.add_command(import_selected_csv)
cli.add_command(reset_database)

# Indexes may not be useful
# cli.add_command(create_indexes)
# cli.add_command(drop_indexes)
# cli.add_command(check_indexes)


def start_cli() -> click.Group:
    env_file = find_dotenv()

    load_dotenv(env_file)

    click.secho("DataWagon", fg="magenta", bold=True)
    click.echo(f"Version: {importlib.metadata.version('datawagon')}")
    click.secho(f"Configuration loaded from: {env_file}")
    click.echo(nl=True)

    return cli(obj={})  # type: ignore


def check_db_connection(
    ctx: click.Context, db_manager: PostgresDatabaseManager
) -> bool:
    """Test the connection to the database."""

    if db_manager.test_connection():
        click.echo(click.style("Successfully connected to the database.", fg="green"))
        return True
    else:
        click.echo(click.style("Failed to connect to the database.", fg="red"))
        ctx.abort()


def check_schema(
    ctx: click.Context, db_manager: PostgresDatabaseManager, schema_name: str
) -> bool:
    """Check if the schema exists and prompt to create if it does not."""

    # This will try to create schema if it does not exist
    if not ensure_schema_exists(db_manager, schema_name):
        click.secho(f"Schema '{schema_name}' does not exist.", fg="red")
        ctx.abort()

    click.echo(nl=True)
    click.secho(f"'{schema_name}' is valid schema.", fg="green")
    click.echo(nl=True)
    return True


def ensure_schema_exists(db_manager: PostgresDatabaseManager, schema_name: str) -> bool:
    if not db_manager.check_schema():
        click.secho(f"Schema '{schema_name}' does not exist in the database.", fg="red")
        if click.confirm("Create the schema?"):
            db_manager.ensure_schema_exists()
            if db_manager.check_schema():
                click.secho(f"Schema '{schema_name}' created.", fg="green")
                return True
            else:
                click.secho("Schema creation failed.", fg="red")
                return False
        else:
            return False
    else:
        return True


if __name__ == "__main__":
    start_cli()
