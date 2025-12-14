from typing import List

import click

from datawagon.commands.files_in_local_fs import files_in_local_fs
from datawagon.commands.files_in_storage import files_in_storage
from datawagon.console import error, file_list, newline, table, warning
from datawagon.objects.current_table_data import CurrentDestinationData
from datawagon.objects.file_comparator import FileComparator
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import ManagedFilesToDatabase


@click.command()
@click.pass_context
def compare_local_files_to_bucket(ctx: click.Context) -> List[ManagedFilesToDatabase]:
    """Compare files in source directory to files in storage bucket."""

    matched_files: List[ManagedFilesToDatabase] = ctx.invoke(files_in_local_fs, file_extension="gz")
    current_bucket_files: List[CurrentDestinationData] = ctx.invoke(files_in_storage)

    csv_file_infos: List[ManagedFileMetadata] = [file_info for src in matched_files for file_info in src.files]

    # Use FileComparator class for comparison logic
    comparator = FileComparator()
    file_diff_display_df = comparator.compare_files(csv_file_infos, current_bucket_files)

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

    new_files = comparator.find_new_files(matched_files, current_bucket_files)

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
