import click


@click.command(name="validate-config")
@click.pass_context
def validate_config(ctx: click.Context) -> None:
    """Validate and display the current configuration."""

    config = ctx.obj["CONFIG"]
    file_config = ctx.obj["FILE_CONFIG"]

    click.secho("Application Configuration:", fg="green")
    click.echo(config.json(indent=2))

    click.secho("\nFile Configuration:", fg="green")
    click.echo(file_config.json(indent=2))

