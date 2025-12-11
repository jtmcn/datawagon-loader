from typing import List

import click
import pandas as pd

from datawagon.commands.files_in_local_fs import files_in_local_fs
from datawagon.commands.files_in_storage import files_in_storage
from datawagon.console import error, file_list, newline, table, warning
from datawagon.objects.current_table_data import CurrentDestinationData
from datawagon.objects.file_utils import FileUtils
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import ManagedFilesToDatabase


@click.command()
@click.pass_context
def compare_local_files_to_bucket(ctx: click.Context) -> List[ManagedFilesToDatabase]:
    """Compare files in source directory to files in storage bucket."""

    matched_files: List[ManagedFilesToDatabase] = ctx.invoke(files_in_local_fs, file_extension="gz")
    current_bucket_files: List[CurrentDestinationData] = ctx.invoke(files_in_storage)

    csv_file_infos: List[ManagedFileMetadata] = [file_info for src in matched_files for file_info in src.files]

    file_diff_display_df = _file_diff(csv_file_infos, current_bucket_files)

    newline()
    if len(file_diff_display_df) > 0:
        table(
            data=file_diff_display_df.values.tolist(),
            headers=["Selector", "Bucket File Count", "Local File Count"],
            title="File Comparison",
        )
    else:
        error("No tables found.")
        ctx.abort()

    new_files = _net_new_files(matched_files, current_bucket_files)

    new_csv_file_infos: List[ManagedFileMetadata] = [file_info for src in new_files for file_info in src.files]

    new_file_count = len(new_csv_file_infos)

    newline()
    newline()

    if new_file_count == 0:
        warning("No new files found.")
    else:
        file_list(
            files=[f.file_name for f in new_csv_file_infos],
            max_display=10,
            title=f"Found {new_file_count} new files:",
            count_total=new_file_count,
        )

    return new_files


# TODO: move these functions to an object class


def _file_diff(
    csv_file_infos: List[ManagedFileMetadata],
    current_database_files: List[CurrentDestinationData],
) -> pd.DataFrame:
    """Create a DataFrame which compares files in source directory to files in database."""

    file_utils = FileUtils()
    grouped_files = file_utils.group_by_base_name(csv_file_infos)

    current_database_file_dict = {table_data.base_name: table_data.file_count for table_data in current_database_files}

    all_tables = set(grouped_files.keys()).union(current_database_file_dict.keys())

    data_rows = []

    for base_name in all_tables:
        source_file_count = len(grouped_files.get(base_name, []))
        db_file_count = current_database_file_dict.get(base_name, 0)

        data_rows.append(
            {
                "Base Name": base_name,
                "DB File Count": db_file_count,
                "Source File Count": source_file_count,
            }
        )

    display_table_data = pd.DataFrame(data_rows)

    return display_table_data.sort_values(by=["Base Name"])


def _net_new_files(
    all_source_files_by_table: List[ManagedFilesToDatabase],
    current_database_files: List[CurrentDestinationData],
) -> List[ManagedFilesToDatabase]:
    """Filter source files to only those not yet in destination.

    Compares local source files against files already in the destination bucket
    and returns only the new files that haven't been uploaded yet.

    Args:
        all_source_files_by_table: All local source files grouped by table
        current_database_files: Files currently in destination bucket

    Returns:
        List of file groups containing only net new files
    """
    existing_files: set[str] = set(
        [
            source_file
            for current_database_file in current_database_files
            for source_file in current_database_file.source_files
        ]
    )

    for range_index in range(len(all_source_files_by_table)):
        all_source_files_by_table[range_index].files = sorted(
            [file for file in all_source_files_by_table[range_index].files if (file.file_name not in existing_files)],
            key=lambda x: x.base_name,
        )

    return all_source_files_by_table
