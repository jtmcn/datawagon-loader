
from pathlib import Path
import click
from csv_file_info import CsvFileInfo
from csv_loader import CSVLoader
from file_utils import FileUtils
from database.postgres_database_manager import PostgresDatabaseManager
from validate_parameters import valid_schema, valid_source_dir, valid_url


@click.command()
@click.option("--db-url", type=str, help="Database URL", envvar="POSTGRES_DB_URL")
@click.option(
    "--schema-name", type=str, help="Schema name to use", envvar="POSTGRES_DB_SCHEMA"
)
@click.option(
    "--source-dir",
    type=click.Path(exists=True),
    help="Source directory containing .csv.gz files.",
    envvar="CSV_SOURCE_DIR",
)
def import_csv(db_url: str, schema_name: str, source_dir: str) -> None:
    """Scan a directory for .csv.gz files and import them into a PostgreSQL database."""

    if not valid_url(db_url):
        return

    if not valid_schema(schema_name):
        return

    if not valid_source_dir(source_dir):
        return

    source_path = Path(source_dir)
    file_utils = FileUtils()
    csv_files = file_utils.scan_for_csv_files(source_path)

    db_manager = PostgresDatabaseManager(db_url, schema_name)
    db_manager.ensure_schema_exists()

    csv_file_infos = [
        CsvFileInfo.build_data_item(csv_file) for csv_file in csv_files
    ]

    for csv_info in csv_file_infos:

        loader = CSVLoader(csv_info.file_path)

        data, header = loader.load_data()

        db_manager.create_table_if_not_exists(csv_info.table_name, header)
        db_manager.insert_data(csv_info.table_name, header, data)

    db_manager.close()
    click.echo(
        click.style(
            f"Successfully imported data from {source_dir} into {db_url}", fg="green"
        )
    )
