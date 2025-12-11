from typing import List

import click

from datawagon.commands.files_in_local_fs import files_in_local_fs
from datawagon.console import confirm, error, status, success
from datawagon.objects.file_utils import FileUtils
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import ManagedFilesToDatabase


@click.command()
@click.pass_context
def file_zip_to_gzip(ctx: click.Context) -> None:
    """Convert ZIP files to GZIP format.

    Scans for .zip files in the source directory, prompts user for confirmation,
    then converts each ZIP file to .csv.gz format and removes the original ZIP.

    Args:
        ctx: Click context with application configuration
    """
    # get list of all zip files
    all_matched_files: List[ManagedFilesToDatabase] = ctx.invoke(
        files_in_local_fs, file_extension="zip"
    )

    zip_files: List[ManagedFileMetadata] = []
    for matched_files in all_matched_files:
        for file in matched_files.files:
            if file.file_name.endswith("zip"):
                zip_files.append(file)

    confirm(
        f"Found {len(zip_files)} zip files. Convert to gzip and remove zip?",
        default=False,
        abort=True,
    )

    file_utils = FileUtils()
    for zip_file in zip_files:
        status(f"Converting {zip_file.file_path} to gzip...")
        try:
            file_outputs = file_utils.csv_zip_to_gzip(
                zip_file.file_path, remove_original_zip=True
            )
            if file_outputs:
                for output_file in file_outputs:
                    success(f"Created: {output_file}")
                success(
                    f"Converted {len(file_outputs)} CSV files from {zip_file.file_name}"
                )
            else:
                error("No files created")
        except ValueError as e:
            error(f"Error: {e}")
        except Exception as e:
            error(f"Conversion failed: {e}")
