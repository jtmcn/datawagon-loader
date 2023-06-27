from typing import List

import click

from datawagon.objects.current_table_data import CurrentTableData
from datawagon.objects.database_manager import DatabaseManager


@click.command()
@click.pass_context
def check_database(ctx: click.Context) -> List[CurrentTableData]:
    """Check if the schema exists and display existing tables and number of rows."""

    db_manager = ctx.obj["DB_CONNECTION"]

    # This will try to create schema if it does not exist
    if not _ensure_schema_exists(db_manager, ctx.obj["CONFIG"].db_schema):
        click.secho("Schema does not exist.", fg="red")
        ctx.abort()

    click.echo(nl=True)

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


def _ensure_schema_exists(db_manager: DatabaseManager, schema_name: str) -> bool:
    if not db_manager.check_schema():
        click.secho(f"Schema '{schema_name}' does not exist in the database.", fg="red")
        if click.confirm("Do you want to create the schema?"):
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


def _current_tables(db_manager: DatabaseManager) -> List[CurrentTableData]:
    tables = db_manager.table_names()
    all_table_data = []
    with click.progressbar(
        length=len(tables),
        label=click.style("Retrieving existing file data from database ", fg="blue"),
        show_eta=False,
    ) as table_progress:
        for table in tables:
            table_df = db_manager.files_in_table_df(table)
            file_list = table_df["_file_name"].tolist()
            table_data = CurrentTableData(
                table, table_df["row_count"].sum(), len(file_list), file_list
            )
            all_table_data.append(table_data)
            table_progress.update(1)

    return all_table_data
