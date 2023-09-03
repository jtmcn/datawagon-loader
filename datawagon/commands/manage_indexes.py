import click

from datawagon.database.index_manager import IndexManager


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.pass_context
def create_indexes(ctx: click.Context) -> None:
    """Create indexes on all tables in the selected schema."""
    index_manager = IndexManager(ctx.obj["DB_CONNECTION"])
    index_manager.create_index_on_all_tables()
    click.secho("Indexes created on all tables.", fg="green")


@cli.command()
@click.pass_context
def drop_indexes(ctx: click.Context) -> None:
    index_manager = IndexManager(ctx.obj["DB_CONNECTION"])
    index_manager.drop_index_on_all_tables()
    click.secho("All indexes dropped", fg="yellow")


@click.command()
@click.pass_context
def check_indexes(ctx: click.Context) -> None:
    index_manager = IndexManager(ctx.obj["DB_CONNECTION"])
    df = index_manager.get_all_indexes()
    click.secho(df)  # type: ignore


if __name__ == "__main__":
    cli()
