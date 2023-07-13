import subprocess
import sys
from collections import namedtuple

import click
import toml
from commands.check_database import check_database
from commands.check_db_connection import check_db_connection
from commands.check_files import check_files
# from commands.manage_indexes import create_indexes, drop_indexes, check_indexes
from commands.compare import compare_files_to_database
from commands.import_all_csv import import_all_csv
from commands.import_single_csv import import_selected_csv
from commands.reset_database import reset_database
from dotenv import load_dotenv
from objects.database_manager import DatabaseManager
from objects.parameter_validator import ParameterValidator


@click.group(chain=True)
@click.option("--db-url", type=str, help="Database URL", envvar="DW_POSTGRES_DB_URL")
@click.option("--db-schema", type=str, help="Schema name to use", envvar="DW_DB_SCHEMA")
@click.option(
    "--csv-source-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    help="Source directory containing .csv, .csv.zip or .csv.gz files.",
    envvar="DW_CSV_SOURCE_DIR",
)
@click.pass_context
def cli(ctx: click.Context, db_url: str, db_schema: str, csv_source_dir: str) -> None:
    if not ParameterValidator(db_url, db_schema, csv_source_dir).are_valid_parameters:
        ctx.abort()

    AppConfig = namedtuple("AppConfig", ["db_schema", "csv_source_dir"])

    db_connection = DatabaseManager(db_url, db_schema)

    # if on mac, prevent computer from sleeping (display, system, disk)
    if "darwin" in sys.platform:
        subprocess.Popen(["caffeinate", "-dim"])

    ctx.obj["DB_CONNECTION"] = db_connection
    ctx.obj["CONFIG"] = AppConfig(db_schema, csv_source_dir)

    ctx.obj["GLOBAL"] = {}

    ctx.call_on_close(db_connection.close)


cli.add_command(reset_database)
cli.add_command(check_db_connection)
cli.add_command(check_database)
cli.add_command(check_files)
cli.add_command(compare_files_to_database)
cli.add_command(import_all_csv)
cli.add_command(import_selected_csv)
cli.add_command(reset_database)

# Indexes may not be useful
# cli.add_command(create_indexes)
# cli.add_command(drop_indexes)
# cli.add_command(check_indexes)


if __name__ == "__main__":
    load_dotenv()

    # print(f"Version: {importlib.metadata.version('datawagon')}")
    version = toml.load("pyproject.toml")["tool"]["poetry"]["version"]
    print(f"Version: {version}")

    cli(obj={})  # type: ignore
