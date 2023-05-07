import click

from datawagon.postgres_database_manager import PostgresDatabaseManager


@click.command()
@click.option("--db-url", type=str, help="Database URL", envvar="POSTGRES_DB_URL")
@click.option(
    "--schema-name", type=str, help="Schema name to use", envvar="POSTGRES_DB_SCHEMA"
)
def reset_database(db_url: str, schema_name: str):
    """Reset the database by dropping all tables and views in the selected schema."""
    click.echo(click.style("This command will drop all tables and views in the selected schema.", bg="yellow"))
    if not click.confirm("Are you sure you want to continue?"):
        return

    db_manager = PostgresDatabaseManager(db_url, schema_name)
    if not db_manager.test_connection():
        click.echo("Unable to connect to the database. Please check the connection settings.")
        return

    db_manager.drop_all_tables_and_views()
    click.echo(f"All tables and views in schema '{schema_name}' have been dropped.")

if __name__ == "__main__":
    reset_database()