import click

from datawagon.objects.database_manager import DatabaseManager


@click.command()
@click.pass_context
def reset_database(ctx: click.Context) -> None:
    """Reset the database by dropping all tables and views in the selected schema."""

    db_manager: DatabaseManager = ctx.obj["DB_CONNECTION"]
    schema_name = ctx.obj["CONFIG"].db_schema

    click.secho(
        f"This command will drop all tables and views in the selected schema: '{schema_name}'"
        + "\nALL DATA WILL BE LOST!",
        bg="yellow",
        bold=True,
    )
    if not click.confirm("Are you sure you want to continue?"):
        return

    if not db_manager.test_connection():
        click.echo(
            "Unable to connect to the database. Please check the connection settings."
        )
        return

    db_manager.drop_all_tables_and_views()
    click.echo(f"All tables and views in schema '{schema_name}' have been dropped.")
