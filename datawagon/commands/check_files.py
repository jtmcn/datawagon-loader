
from pathlib import Path
import click

from datawagon.csv_file_info import CsvFileInfo
from datawagon.file_utils import FileUtils
from datawagon.validate_parameters import valid_source_dir


@click.command()
@click.option(
    "--source-dir",
    type=click.Path(exists=True),
    help="Source directory containing .csv.gz and/or .csv.zip files.",
    envvar="CSV_SOURCE_DIR",
)
def check_files(source_dir: str) -> None:
    """Scan a directory for .csv.gz files and display the number of files grouped by table_name."""

    if not valid_source_dir(source_dir):
        return

    file_utils = FileUtils()
    source_path = Path(source_dir)

    csv_files = file_utils.scan_for_csv_files(source_path)

    list_of_file_info = [
        CsvFileInfo.build_data_item(csv_file) for csv_file in csv_files
    ]

    if len(list_of_file_info) == 0:
        click.echo(click.style(f"No .csv.gz or .csv.zip files found in source_dir:{source_dir}", fg="red"))
        return

    duplicates = file_utils.check_for_duplicate_files(list_of_file_info)

    if len(duplicates) > 0:
        click.echo(click.style("Duplicate files found:", fg="red"))
        for duplicate in duplicates:
            click.echo(f"  - {duplicate.file_path}")

        click.echo(
            click.style("Please remove duplicate files and try again.", fg="red")
        )
        return


    different_file_versions = file_utils.check_for_different_file_versions(list_of_file_info)
    if different_file_versions:
        click.echo(click.style("Different file versions found for the same table name:", fg="red"))
        for file_infos in different_file_versions:
            click.echo(f"Table name: {file_infos[0].table_name}")
            file_infos.sort(key=lambda x: x.file_version)
            for file_info in file_infos:
                click.echo(f"  - {file_info.file_name} ({file_info.file_version})")
        return
        
    grouped_files = file_utils.group_by_table_name(list_of_file_info)

    click.echo(click.style("Number of files grouped by table_name:", bg="blue"))
    for table_name, files in grouped_files.items():
        click.echo(f"{table_name}: {len(files)} files")
