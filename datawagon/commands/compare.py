from typing import List

import click
import pandas as pd
from tabulate import tabulate

from datawagon.commands.files_in_database import files_in_database
from datawagon.commands.files_in_local_fs import files_in_local_fs
from datawagon.commands.files_in_storage import files_in_storage
from datawagon.objects.current_table_data import CurrentDestinationData
from datawagon.objects.file_utils import FileUtils
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import ManagedFilesToDatabase


@click.command()
@click.pass_context
def compare_local_files_to_database(ctx: click.Context) -> List[ManagedFilesToDatabase]:
    """Compare files in source directory to files in database."""

    matched_files: List[ManagedFilesToDatabase] = ctx.invoke(files_in_local_fs)
    current_database_files: List[CurrentDestinationData] = ctx.invoke(files_in_database)

    csv_file_infos: List[ManagedFileMetadata] = [
        file_info for src in matched_files for file_info in src.files
    ]

    file_diff_display_df = _file_diff(csv_file_infos, current_database_files)

    click.echo(nl=True)
    if len(file_diff_display_df) > 0:
        click.secho(
            tabulate(
                # type ignore because tabulate does support pandas dataframes
                file_diff_display_df,  # type: ignore
                headers=["Table", "DB File Count", "Local File Count"],
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

    new_csv_file_infos: List[ManagedFileMetadata] = [
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


@click.command()
@click.pass_context
def compare_local_files_to_bucket(ctx: click.Context) -> List[ManagedFilesToDatabase]:
    """Compare files in source directory to files in storage bucket."""

    matched_files: List[ManagedFilesToDatabase] = ctx.invoke(
        files_in_local_fs, file_extension="gz"
    )
    current_bucket_files: List[CurrentDestinationData] = ctx.invoke(files_in_storage)

    csv_file_infos: List[ManagedFileMetadata] = [
        file_info for src in matched_files for file_info in src.files
    ]

    file_diff_display_df = _file_diff(csv_file_infos, current_bucket_files)

    click.echo(nl=True)
    if len(file_diff_display_df) > 0:
        click.secho(
            tabulate(
                # type ignore because tabulate does support pandas dataframes
                file_diff_display_df,  # type: ignore
                headers=["Selector", "Bucket File Count", "Local File Count"],
                tablefmt="simple",
                showindex=False,
                numalign="right",
                intfmt=",",
            )
        )
    else:
        click.secho("No tables found.", fg="red")
        ctx.abort()

    new_files = _net_new_files(matched_files, current_bucket_files)

    new_csv_file_infos: List[ManagedFileMetadata] = [
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
    csv_file_infos: List[ManagedFileMetadata],
    current_database_files: List[CurrentDestinationData],
) -> pd.DataFrame:
    """Create a DataFrame which compares files in source directory to files in database."""

    file_utils = FileUtils()
    grouped_files = file_utils.group_by_base_name(csv_file_infos)

    current_database_file_dict = {
        table_data.base_name: table_data.file_count
        for table_data in current_database_files
    }

    all_tables = set(grouped_files.keys()).union(current_database_file_dict.keys())

    data_rows = []

    for base_name in all_tables:
        source_file_count = len(grouped_files.get(base_name, []))
        db_file_count = current_database_file_dict.get(base_name, 0)

        data_rows.append(
            {
                "Table": base_name,
                "DB File Count": db_file_count,
                "Source File Count": source_file_count,
            }
        )

    display_table_data = pd.DataFrame(data_rows)

    return display_table_data.sort_values(by=["Table"])


def _net_new_files(
    all_source_files_by_table: List[ManagedFilesToDatabase],
    current_database_files: List[CurrentDestinationData],
) -> List[ManagedFilesToDatabase]:
    existing_files: set[str] = set(
        [
            source_file
            for current_database_file in current_database_files
            for source_file in current_database_file.source_files
        ]
    )

    for range_index in range(len(all_source_files_by_table)):
        all_source_files_by_table[range_index].files = sorted(
            [
                file
                for file in all_source_files_by_table[range_index].files
                if (file.file_name_without_extension not in existing_files)
            ],
            key=lambda x: x.base_name,
        )

    return all_source_files_by_table
