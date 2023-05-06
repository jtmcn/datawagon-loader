import click
from dotenv import load_dotenv
import collections
from pathlib import Path
from typing import List
# from .gzipped_csv_loader import GzippedCSVLoader
from postgres_database_manager import PostgresDatabaseManager
from csv_file_info import CsvFileInfo
from file_utils import FileUtils

load_dotenv()


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option(
    "--db-url", type=str, help="PostgreSQL database URL.", envvar="POSTGRES_DB_URL"
)
@click.option(
    "--schema-name", type=str, help="Schema name to use", envvar="POSTGRES_SCHEMA_NAME"
)
def test_db_connection(db_url: str, schema_name: str) -> None:
    """Test the connection to the database."""

    if not valid_url(db_url):
        return
    
    print(db_url)
    print(schema_name)

    if not valid_schema(schema_name):
        return

    db_manager = PostgresDatabaseManager(db_url, schema_name)

    if db_manager.test_connection():
        click.echo(click.style("Successfully connected to the database.", fg="green"))
        db_manager.close()
    else:
        click.echo(click.style("Failed to connect to the database.", fg="red"))


@cli.command()
@click.option("--db-url", type=str, help="Database URL", envvar="POSTGRES_DB_URL")
@click.option(
    "--schema-name", type=str, help="Schema name to use", envvar="POSTGRES_SCHEMA_NAME"
)
def check_database(db_url: str, schema_name: str) -> None:
    """Check if the schema exists and display existing tables and number of rows."""

    if not valid_url(db_url):
        return

    if not valid_schema(schema_name):
        return

    db_manager = PostgresDatabaseManager(db_url, schema_name)

    if not db_manager.check_schema():
        click.echo(
            click.style(
                f"Schema '{schema_name}' does not exist in the database.", fg="red"
            )
        )
        if click.confirm("Do you want to create the schema?"):
            db_manager.ensure_schema_exists()
            if db_manager.check_schema():
                click.echo(click.style(f"Schema '{schema_name}' created.", fg="green"))
            else:
                click.echo(click.style("Schema creation failed.", fg="red"))
                return
        else:
            return
    else:
        click.echo(f"Schema '{schema_name}' exists in the database.\n")

    click.echo("Tables and row counts:")
    tables_and_row_counts = db_manager.get_tables_and_row_counts()
    if not tables_and_row_counts:
        click.echo("No tables found.")
    else:
        for table_name, row_count in tables_and_row_counts:
            click.echo(f"{table_name}: {row_count} rows")

    db_manager.close()


@cli.command()
@click.option(
    "--source-dir",
    type=click.Path(exists=True),
    help="Source directory containing .csv.gz files.",
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

    duplicates = file_utils.check_for_duplicate_files(list_of_file_info)

    if len(duplicates) > 0:
        click.echo(click.style("Duplicate files found:", fg="red"))
        for duplicate in duplicates:
            click.echo(f"  - {duplicate}")

        click.echo(
            click.style("Please remove duplicate files and try again.", fg="red")
        )
        return

    grouped_files = file_utils.group_by_table_name(list_of_file_info)

    click.echo("Number of files grouped by table_name:")
    for table_name, files in grouped_files.items():
        click.echo(f"{table_name}: {len(files)} files")


# @click.command()
# @click.option("--db-url", type=str, help="Database URL", envvar="POSTGRES_DB_URL")
# @click.option(
#     "--schema-name", type=str, help="Schema name to use", envvar="POSTGRES_SCHEMA_NAME"
# )
# @click.option(
#     "--source-dir",
#     type=click.Path(exists=True),
#     help="Source directory containing .csv.gz files.",
#     envvar="CSV_SOURCE_DIR",
# )
# def import_csv(db_url: str, schema_name: str, source_dir: str) -> None:
#     """Scan a directory for .csv.gz files and import them into a PostgreSQL database."""

#     if not valid_url(db_url):
#         return

#     if not valid_schema(schema_name):
#         return

#     if not valid_source_dir(source_dir):
#         return

#     source_path = Path(source_dir)
#     file_scanner = FileScanner()
#     csv_files = file_scanner.scan_for_csv_files(source_path)

#     db_manager = PostgresDatabaseManager(db_url, schema_name)
#     db_manager.ensure_schema_exists()

#     for csv_file in csv_files:
#         csv_info = CsvFileInfo.build_data_item(csv_file)
#         loader = GzippedCSVLoader(csv_info.file_path)
#         data, header = loader.load_data()

#         db_manager.create_table_if_not_exists(csv_info.table_name, header)
#         db_manager.insert_data(csv_info.table_name, header, data)

#     db_manager.close()
#     click.echo(
#         click.style(
#             f"Successfully imported data from {source_dir} into {db_url}", fg="green"
#         )
#     )

# THIS DOESN'T FUCKING WORK!!


# def check_for_duplicate_files(file_info_list: List[CsvFileInfo]) -> bool:
#     file_names = [file_info.file_name for file_info in file_info_list]
#     # print(file_names)
#     duplicates = list(
#         set([file_name for file_name in file_names if file_names.count(file_name) > 1])
#     )
#     print("DUPLICATES", duplicates)

#     if duplicates:
#         click.echo(click.style("Duplicate files found:", fg="red"))
#         for duplicate in duplicates:
#             click.echo(f"  - {duplicate}")
#         return True
#     return False


def valid_url(db_url: str) -> bool:
    if not db_url:
        click.echo(
            click.style(
                "Database URL not provided or found in the environment variable 'POSTGRES_DB_URL'.",
                fg="red",
            )
        )
        return False
    return True


def valid_schema(schema_name: str) -> bool:
    if not schema_name:
        click.echo(
            click.style(
                "Schema not provided or found in the environment variable 'POSTGRES_DB_SCHEMA'.",
                fg="red",
            )
        )
        return False

    return True


def valid_source_dir(schema_name: str) -> bool:
    if not schema_name:
        click.echo(
            click.style(
                "CSV Source Directory not provided or found in the environment variable 'CSV_SOURCE_DIR'.",
                fg="red",
            )
        )
        return False

    return True


# Add additional utility commands here, e.g., test_connection, reset_database, display_info.


cli.add_command(test_db_connection)
cli.add_command(check_database)
cli.add_command(check_files)
# cli.add_command(import_csv)

if __name__ == "__main__":
    cli()
