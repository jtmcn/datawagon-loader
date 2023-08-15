from pathlib import Path
from typing import List

import click

from datawagon.objects.csv_file_info_override import CsvFileInfoOverride
from datawagon.objects.file_utils import FileUtils
from datawagon.objects.source_file_scanner import (
    SourceFileScanner,
    SourceFilesToDatabase,
)


@click.command()
@click.pass_context
def scan_files(ctx: click.Context) -> List[SourceFilesToDatabase]:
    """Scan a directory for .csv.gz files and display the number of files grouped by table_name."""

    source_dir = ctx.obj["CONFIG"].csv_source_dir
    app_config = ctx.obj["CONFIG"]

    file_utils = FileUtils()
    source_path = Path(source_dir)

    click.secho(f"Scanning for .csv files in {source_path}...", fg="blue")

    matched_files = SourceFileScanner(app_config).matched_files()

    print(matched_files)

    if len(matched_files) == 0:
        click.secho(f"No .csv files found in source directory: {source_dir}", fg="red")
        ctx.abort()

    for files_by_table in matched_files:
        click.secho(
            f"Matched {len(files_by_table.files)} files with name: {files_by_table.file_selector}"
        )

    csv_file_infos: List[CsvFileInfoOverride] = [
        file_info for src in matched_files for file_info in src.files
    ]

    duplicates = file_utils.check_for_duplicate_files(csv_file_infos)

    if len(duplicates) > 0:
        click.secho("Duplicate files found:", fg="red")
        for duplicate in duplicates:
            click.echo(f"  - {duplicate.file_path}")

        click.secho("Please remove duplicate files and try again.", fg="red")

        ctx.abort()

    different_file_versions = file_utils.check_for_different_file_versions(
        csv_file_infos
    )

    if different_file_versions:
        click.secho("Different file versions found for the same table name:", fg="red")
        for file_infos in different_file_versions:
            file_infos.sort(key=lambda x: x.file_version)
            for file_info in file_infos:
                click.echo(f"  - {file_info.file_name} ({file_info.file_version})")
        ctx.abort()

    click.echo(nl=True)
    print(matched_files)
    return matched_files
