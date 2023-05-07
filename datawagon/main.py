import click
from dotenv import load_dotenv
import collections
from pathlib import Path
from typing import List
from commands.reset_database import reset_database
from commands.test_db_connection import test_db_connection
from commands.check_database import check_database
from commands.check_files import check_files
from commands.import_csv import import_csv

load_dotenv()

@click.group()
def cli() -> None:
    pass

# Add additional utility commands here, e.g., test_connection, reset_database, display_info.

cli.add_command(reset_database)
cli.add_command(test_db_connection)
cli.add_command(check_database)
cli.add_command(check_files)
cli.add_command(import_csv)

if __name__ == "__main__":
    cli()
