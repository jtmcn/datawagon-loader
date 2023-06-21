from pathlib import Path
import click

from objects.csv_file_info import CsvFileInfo
from objects.file_utils import FileUtils


@click.command()
@click.pass_context
def check_files(ctx: click.Context) -> list[CsvFileInfo]:
    """Scan a directory for .csv.gz files and display the number of files grouped by table_name."""

    source_dir = ctx.obj["CONFIG"].csv_source_dir

    file_utils = FileUtils()
    source_path = Path(source_dir)

    click.secho(f"Scanning {source_path} for .csv files...", fg="blue")

    csv_files = file_utils.scan_for_csv_files(source_path)

    list_of_file_info = [
        CsvFileInfo.build_data_item(csv_file) for csv_file in csv_files
    ]

    if len(list_of_file_info) == 0:
        click.secho(f"No .csv files found in source directory: {source_dir}", fg="red")
        ctx.abort()

    duplicates = file_utils.check_for_duplicate_files(list_of_file_info)

    if len(duplicates) > 0:
        click.secho("Duplicate files found:", fg="red")
        for duplicate in duplicates:
            click.echo(f"  - {duplicate.file_path}")

        click.secho("Please remove duplicate files and try again.", fg="red")

        ctx.abort()

    different_file_versions = file_utils.check_for_different_file_versions(
        list_of_file_info
    )

    if different_file_versions:
        click.secho("Different file versions found for the same table name:", fg="red")
        for file_infos in different_file_versions:
            file_infos.sort(key=lambda x: x.file_version)
            for file_info in file_infos:
                click.echo(f"  - {file_info.file_name} ({file_info.file_version})")
        ctx.abort()

    click.secho(f"{len(list_of_file_info)} files found in source directory")

    click.echo(nl=True)

    return list_of_file_info
