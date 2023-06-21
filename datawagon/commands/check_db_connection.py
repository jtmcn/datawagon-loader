import click

from objects.database_manager import DatabaseManager


@click.command()
@click.pass_context
def check_db_connection(ctx: click.Context) -> bool:
    """Test the connection to the database."""

    db_manager: DatabaseManager = ctx.obj['DB_CONNECTION']

    if db_manager.test_connection():
        click.echo(click.style("Successfully connected to the database.", fg="green"))
        return True
    else:
        click.echo(click.style("Failed to connect to the database.", fg="red"))
        return False
