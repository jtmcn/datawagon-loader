

import click

from datawagon.postgres_database_manager import PostgresDatabaseManager
from datawagon.validate_parameters import valid_schema, valid_url

@click.command()
@click.option("--db-url", type=str, help="Database URL", envvar="POSTGRES_DB_URL")
@click.option(
    "--schema-name", type=str, help="Schema name to use", envvar="POSTGRES_DB_SCHEMA"
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