import click

from datawagon.database.postgres_database_manager import PostgresDatabaseManager


@click.command()
@click.pass_context
def reset_database(ctx: click.Context) -> None:
    """Reset the database by dropping all tables and views in the selected schema."""

    db_manager: PostgresDatabaseManager = ctx.obj["DB_CONNECTION"]
    if not db_manager.is_valid_connection:
        ctx.abort()

    schema_name = ctx.obj["CONFIG"].db_schema

    click.secho(
        "This command will DELETE ALL DATA "
        + f"\non server: '{db_manager.hostname}'"
        + f"\nin database: '{db_manager.db_name}'"
        + f"\nwithin the schema: '{schema_name}' "
        + "\nALL DATA WILL BE LOST!",
        bg="yellow",
        bold=True,
    )
    click.echo(nl=True)

    if not click.confirm("Are you sure you want to continue?"):
        return

    click.echo(nl=True)

    if not db_manager.test_connection():
        click.secho(
            "Unable to connect to the database. Please check the connection settings.",
            fg="red",
        )
        return

    db_manager.drop_schema()
    click.echo(f"All tables, views and schema '{schema_name}' have been dropped.")
