from typing import List

import click

from datawagon.commands.files_in_local_fs import files_in_local_fs
from datawagon.objects.file_utils import FileUtils
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import ManagedFilesToDatabase


@click.command()
@click.pass_context
def file_zip_to_gzip(ctx: click.Context) -> None:
    # get list of all zip files
    all_matched_files: List[ManagedFilesToDatabase] = ctx.invoke(
        files_in_local_fs, file_extension="zip"
    )

    zip_files: List[ManagedFileMetadata] = []
    for matched_files in all_matched_files:
        for file in matched_files.files:
            if file.file_name.endswith("zip"):
                zip_files.append(file)

    click.confirm(
        f"Found {len(zip_files)} zip files. Convert to gzip and remove zip?",
        default=False,
        abort=True,
    )

    file_utils = FileUtils()
    for zip_file in zip_files:
        click.secho(f"Converting {zip_file.file_path} to gzip...", fg="blue")
        file_output = file_utils.csv_zip_to_gzip(
            zip_file.file_path, remove_original_zip=True
        )
        if file_output:
            click.secho(f"Success: {file_output} ", fg="green")
        else:
            click.secho("ERROR", fg="red")
