from typing import List

import click

from datawagon.commands.check_db_connection import check_db_connection
from datawagon.commands.check_schema import check_schema
from datawagon.commands.compare import compare_files_to_database
from datawagon.objects.csv_file_info import CsvFileInfo
from datawagon.objects.csv_loader import CSVLoader
from datawagon.objects.database_manager import DatabaseManager


@click.command(name="import")
@click.pass_context
def import_all_csv(ctx: click.Context) -> None:
    """Scan a directory for .csv files and import them into a PostgreSQL database."""

    config = ctx.obj["CONFIG"]

    db_manager: DatabaseManager = ctx.obj["DB_CONNECTION"]

    if ctx.invoke(check_db_connection) and ctx.invoke(check_schema):
        csv_file_infos: List[CsvFileInfo] = ctx.invoke(compare_files_to_database)

        if len(csv_file_infos) != 0:
            click.echo(nl=True)
            click.echo(nl=True)

            click.confirm(
                f"Import {len(csv_file_infos)} new files?", default=False, abort=True
            )

            click.echo(nl=True)

            has_errors = False
            for csv_info in csv_file_infos:
                loader = CSVLoader(csv_info)

                df = loader.load_data()

                click.echo(
                    f"Importing {csv_info.content_owner}-{csv_info.file_date_key} into {csv_info.table_name}... ",
                    nl=False,
                )

                success_count = db_manager.load_dataframe_into_database(
                    df, csv_info.table_name
                )

                if success_count == -1:
                    has_errors = True
                    click.secho(f"Import failed for {csv_info.file_name}", fg="red")
                else:
                    click.secho(f"inserted {success_count:,} rows", fg="green")

            click.echo(nl=True)

            if has_errors:
                click.secho(
                    f"Import errors from {config.csv_source_dir}", fg="red", bold=True
                )
            else:
                click.secho(
                    f"Successfully imported data from {config.csv_source_dir} into database",
                    fg="green",
                )

            # TODO: check_database again and display new row difference (?)
