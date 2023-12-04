from pathlib import Path

import click

from datawagon.database.postgres_database_manager import PostgresDatabaseManager
from datawagon.objects.app_config import AppConfig
from datawagon.objects.csv_loader import CSVLoader
from datawagon.objects.managed_file_scanner import ManagedFileScanner


@click.command(name="import-selected-to-postgres")
@click.option(
    "--replace",
    type=click.BOOL,
    default=False,
    show_default=True,
    help="Replace all table data with file instead of default append",
)
@click.argument(
    "file_path",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    required=True,
)
@click.argument("file_base_name", type=str, required=True)
@click.pass_context
def import_selected_csv(
    ctx: click.Context, replace: bool, file_path: str, file_base_name: str
) -> None:
    """Import a single .csv file into the database."""

    # TODO: change current "replace" option to truncate,
    # and use "replace" to delete and replace single file

    # click file path passed in a string
    csv_file_path = Path(file_path)

    app_config: AppConfig = ctx.obj["CONFIG"]

    source_file_mapper = ManagedFileScanner(
        app_config.csv_source_config, app_config.csv_source_dir
    ).matched_file(csv_file_path, file_base_name, replace)

    if not source_file_mapper or not source_file_mapper.files:
        click.secho("File not matched in source_config.toml", fg="red")
        click.echo(nl=True)
        ctx.abort()

    csv_info = source_file_mapper.files[0]

    db_manager: PostgresDatabaseManager = ctx.obj["DB_CONNECTION"]

    if not db_manager.is_valid_connection:
        ctx.abort()

    if not replace and db_manager.check_if_file_imported(
        csv_info.file_name, csv_info.table_name
    ):
        click.secho(f"File already imported: {csv_info.file_name}", fg="yellow")
        click.echo(nl=True)
        ctx.abort()

    loader = CSVLoader(csv_info)

    df = loader.load_data()

    if db_manager.load_dataframe_into_database(
        df, csv_info.table_name, csv_info.table_append_or_replace
    ):
        click.secho("Successfully imported data into database", fg="green")
    else:
        click.secho(f"Import failed for: {csv_info.file_name}", fg="red")
