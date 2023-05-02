import os
import click
from pathlib import Path
from typing import List
from .gzipped_csv_loader import GzippedCSVLoader
from .postgres_database_manager import PostgresDatabaseManager
from .file_scanner import FileScanner
from .csv_file_info import CsvFileInfo


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option(
    "--db-url", type=str, help="PostgreSQL database URL.", envvar="POSTGRES_DB_URL"
)
def test_db_connection(db_url: str, schema_name: str) -> None:
    """Test the connection to the database."""

    if not valid_url(db_url):
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


@click.command()
@click.option("--db-url", type=str, help="Database URL", envvar="POSTGRES_DB_URL")
@click.option(
    "--schema-name", type=str, help="Schema name to use", envvar="POSTGRES_SCHEMA_NAME"
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
    file_scanner = FileScanner()
    csv_files = file_scanner.scan_for_csv_files(source_path)

    db_manager = PostgresDatabaseManager(db_url, schema_name)
    db_manager.ensure_schema_exists()

    for csv_file in csv_files:
        csv_info = CsvFileInfo.build_data_item(csv_file)
        loader = GzippedCSVLoader(csv_info.file_path)
        data, header = loader.load_data()

        db_manager.create_table_if_not_exists(csv_info.table_name, header)
        db_manager.insert_data(csv_info.table_name, header, data)

    db_manager.close()
    click.echo(
        click.style(
            f"Successfully imported data from {source_dir} into {db_url}", fg="green"
        )
    )


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


cli.add_command(import_csv)

if __name__ == "__main__":
    cli()
