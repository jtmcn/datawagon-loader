from typing import List

import click
import pandas as pd
from tabulate import tabulate

from datawagon.commands.check_database import check_database
from datawagon.commands.check_files import check_files
from datawagon.objects.csv_file_info import CsvFileInfo
from datawagon.objects.current_table_data import CurrentTableData
from datawagon.objects.file_utils import FileUtils


@click.command()
@click.pass_context
def compare_files_to_database(ctx: click.Context) -> List[CsvFileInfo]:
    """Compare files in source directory to files in database."""

    csv_file_infos: List[CsvFileInfo] = ctx.invoke(check_files)
    current_database_files: List[CurrentTableData] = ctx.invoke(check_database)

    file_diff_display_df = _file_diff(csv_file_infos, current_database_files)

    click.echo(nl=True)
    if len(file_diff_display_df) > 0:
        click.secho(
            tabulate(
                # type ignore because tabulate does support pandas dataframes
                file_diff_display_df,  # type: ignore
                headers=["Table", "DB File Count", "Source File Count"],
                tablefmt="simple",
                showindex=False,
                numalign="right",
                intfmt=",",
            )
        )
    else:
        click.secho("No tables found.", fg="red")
        ctx.abort()

    new_files = _net_new_files(csv_file_infos, current_database_files)

    new_file_count = len(new_files)

    click.echo(nl=True)
    click.echo(nl=True)

    if new_file_count == 0:
        click.secho("No new files found.", fg="yellow")
    else:
        display_limit = 10
        i = 0
        click.secho(f"Found {new_file_count} new files:", fg="green")
        for file in new_files:
            if i >= display_limit:
                break
            click.secho(f"{file.file_name}")
            i += 1
        if new_file_count > display_limit:
            click.secho(f"...including {new_file_count - display_limit} more.")

    return new_files


def _file_diff(
    csv_file_infos: List[CsvFileInfo], current_database_files: List[CurrentTableData]
) -> pd.DataFrame:
    """Create a DataFrame which compares files in source directory to files in database."""

    file_utils = FileUtils()
    grouped_files = file_utils.group_by_table_name(csv_file_infos)

    current_database_file_dict = {
        table_data.table_name: table_data.file_count
        for table_data in current_database_files
    }

    all_tables = set(grouped_files.keys()).union(current_database_file_dict.keys())

    data_rows = []

    for table_name in all_tables:
        source_file_count = len(grouped_files.get(table_name, []))
        db_file_count = current_database_file_dict.get(table_name, 0)

        data_rows.append(
            {
                "Table": table_name,
                "DB File Count": db_file_count,
                "Source File Count": source_file_count,
            }
        )

    display_table_data = pd.DataFrame(data_rows)

    return display_table_data.sort_values(by=["Table"])


def _net_new_files(
    csv_file_infos: List[CsvFileInfo], current_database_files: List[CurrentTableData]
) -> List[CsvFileInfo]:
    existing_files: set[str] = set(
        [
            source_file
            for current_database_file in current_database_files
            for source_file in current_database_file.source_files
        ]
    )

    new_files = [
        file
        for file in csv_file_infos
        if (file.file_name_without_extension not in existing_files)
    ]

    return sorted(new_files, key=lambda x: x.table_name)
