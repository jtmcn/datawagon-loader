from typing import List

import click

from datawagon.commands.compare import compare_files_to_database
from datawagon.objects.csv_loader import CSVLoader
from datawagon.objects.postgres_database_manager import PostgresDatabaseManager
from datawagon.objects.source_file_metadata import SourceFileMetadata
from datawagon.objects.source_file_scanner import SourceFilesToDatabase


@click.command(name="import")
@click.pass_context
def import_all_csv(ctx: click.Context) -> None:
    """Scan a directory for .csv files and import them into a PostgreSQL database."""

    config = ctx.obj["CONFIG"]

    db_manager: PostgresDatabaseManager = ctx.obj["DB_CONNECTION"]

    if not db_manager.is_valid_connection:
        ctx.abort()

    matched_new_files: List[SourceFilesToDatabase] = ctx.invoke(
        compare_files_to_database
    )

    csv_file_infos: List[SourceFileMetadata] = [
        file_info for src in matched_new_files for file_info in src.files
    ]

    if len(csv_file_infos) != 0:
        click.echo(nl=True)
        click.echo(nl=True)

        click.confirm(
            f"Import {len(csv_file_infos)} new files?", default=False, abort=True
        )

        click.echo(nl=True)

        has_errors = False
        for csv_info in csv_file_infos:
            click.echo(
                f"Importing {csv_info.file_name_without_extension} into {csv_info.table_name}... ",
                nl=False,
            )

            loader = CSVLoader(csv_info)

            df = loader.load_data()

            success_count = db_manager.load_dataframe_into_database(
                df, csv_info.table_name
            )

            if success_count == -1:
                has_errors = True
                click.echo(nl=True)
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
