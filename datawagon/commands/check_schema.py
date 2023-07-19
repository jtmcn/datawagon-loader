import click

from datawagon.objects.database_manager import DatabaseManager


@click.command()
@click.pass_context
def check_schema(ctx: click.Context) -> bool:
    """Check if the schema exists and prompt to create if it does not."""

    db_manager = ctx.obj["DB_CONNECTION"]
    schema_name = ctx.obj["CONFIG"].db_schema

    # This will try to create schema if it does not exist
    if not _ensure_schema_exists(db_manager, schema_name):
        click.secho("Schema does not exist.", fg="red")
        ctx.abort()

    click.echo(nl=True)
    click.secho(f"Schema valid: '{schema_name}'", fg="green")
    return True


def _ensure_schema_exists(db_manager: DatabaseManager, schema_name: str) -> bool:
    if not db_manager.check_schema():
        click.secho(f"Schema '{schema_name}' does not exist in the database.", fg="red")
        if click.confirm("Do you want to create the schema?"):
            db_manager.ensure_schema_exists()
            if db_manager.check_schema():
                click.secho(f"Schema '{schema_name}' created.", fg="green")
                return True
            else:
                click.secho("Schema creation failed.", fg="red")
                return False
        else:
            return False
    else:
        return True
