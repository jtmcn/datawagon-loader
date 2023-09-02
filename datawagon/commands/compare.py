from typing import List

import click
import pandas as pd
from tabulate import tabulate

from datawagon.commands.files_in_database import files_in_database
from datawagon.commands.scan_files import scan_files
from datawagon.objects.csv_file_info_override import CsvFileInfoOverride
from datawagon.objects.current_table_data import CurrentTableData
from datawagon.objects.file_utils import FileUtils
from datawagon.objects.source_file_scanner import SourceFilesToDatabase


@click.command()
@click.pass_context
def compare_files_to_database(ctx: click.Context) -> List[SourceFilesToDatabase]:
    """Compare files in source directory to files in database."""

    matched_files: List[SourceFilesToDatabase] = ctx.invoke(scan_files)
    current_database_files: List[CurrentTableData] = ctx.invoke(files_in_database)

    csv_file_infos: List[CsvFileInfoOverride] = [
        file_info for src in matched_files for file_info in src.files
    ]

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

    new_files = _net_new_files(matched_files, current_database_files)

    new_csv_file_infos: List[CsvFileInfoOverride] = [
        file_info for src in new_files for file_info in src.files
    ]

    new_file_count = len(new_csv_file_infos)

    click.echo(nl=True)
    click.echo(nl=True)

    if new_file_count == 0:
        click.secho("No new files found.", fg="yellow")
    else:
        display_limit = 10
        i = 0
        click.secho(f"Found {new_file_count} new files:", fg="green")
        for file in new_csv_file_infos:
            if i >= display_limit:
                break
            click.secho(f"{file.file_name}")
            i += 1
        if new_file_count > display_limit:
            click.secho(f"...including {new_file_count - display_limit} more.")

    return new_files


# TODO: move these functions to an object class


def _file_diff(
    csv_file_infos: List[CsvFileInfoOverride],
    current_database_files: List[CurrentTableData],
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
    all_source_files_by_table: List[SourceFilesToDatabase],
    current_database_files: List[CurrentTableData],
) -> List[SourceFilesToDatabase]:
    existing_files: set[str] = set(
        [
            source_file
            for current_database_file in current_database_files
            for source_file in current_database_file.source_files
        ]
    )

    # new_files = []
    # maintain list of source files by table, but remove existing_files
    # from the inner files []

    # for source_files_by_table in all_source_files_by_table:
    for range_index in range(len(all_source_files_by_table)):
        # source_files_by_table = all_source_files_by_table[range_index]
        all_source_files_by_table[range_index].files = sorted(
            [
                file
                for file in all_source_files_by_table[range_index].files
                if (file.file_name_without_extension not in existing_files)
            ],
            key=lambda x: x.table_name,
        )

    # new_files = [
    #     file
    #     for file in source_files_by_table
    #     if (file.file_name_without_extension not in existing_files)
    # ]

    return all_source_files_by_table
