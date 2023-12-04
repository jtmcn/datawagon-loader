from typing import List

import click

from datawagon.database.postgres_database_manager import PostgresDatabaseManager
from datawagon.objects.current_table_data import CurrentDestinationData


@click.command()
@click.pass_context
def files_in_database(ctx: click.Context) -> List[CurrentDestinationData]:
    """Display existing tables and number of rows."""

    db_manager = ctx.obj["DB_CONNECTION"]

    if not db_manager.is_valid_connection:
        ctx.abort()

    existing_table_files = _current_tables(db_manager)

    db_count = len(
        [
            source_file
            for existing_table_files in existing_table_files
            for source_file in existing_table_files.source_files
        ]
    )

    click.secho(f"{db_count} files previously imported")
    click.echo(nl=True)

    return existing_table_files


def _current_tables(
    db_manager: PostgresDatabaseManager,
) -> List[CurrentDestinationData]:
    tables = db_manager.table_names()
    all_table_data = []
    with click.progressbar(
        length=len(tables),
        label=click.style("Retrieving existing file data from database ", fg="blue"),
        show_eta=False,
    ) as table_progress:
        for table in tables:
            table_exists = db_manager.check_table(table)
            if table_exists:
                table_df = db_manager.files_in_table_df(table)
                file_list = table_df["_file_name"].tolist()
                table_data = CurrentDestinationData(
                    base_name=table,
                    file_count=len(file_list),
                    source_files=file_list,
                )
                all_table_data.append(table_data)
                table_progress.update(1)

    return all_table_data
