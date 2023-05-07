
import click

from datawagon.postgres_database_manager import PostgresDatabaseManager
from datawagon.validate_parameters import valid_schema, valid_url

@click.command()
@click.option(
    "--db-url", type=str, help="PostgreSQL database URL.", envvar="POSTGRES_DB_URL"
)
@click.option(
    "--schema-name", type=str, help="Schema name to use", envvar="POSTGRES_DB_SCHEMA"
)
def test_db_connection(db_url: str, schema_name: str) -> None:
    """Test the connection to the database."""

    if not valid_url(db_url):
        return

    if not valid_schema(schema_name):
        return

    db_manager = PostgresDatabaseManager(db_url, schema_name)

    if db_manager.test_connection():
        click.echo(click.style("Successfully connected to the database.", fg="green"))
        db_manager.close()
    else:
        click.echo(click.style("Failed to connect to the database.", fg="red"))

