
import click


def valid_url(db_url: str) -> bool:
    if not db_url:
        click.echo(
            click.style(
                "Database URL not provided or found in the environment variable 'POSTGRES_DB_URL'.",
                fg="red",
            )
        )
        return False
    return True


def valid_schema(schema_name: str) -> bool:
    if not schema_name:
        click.echo(
            click.style(
                "Schema not provided or found in the environment variable 'POSTGRES_DB_SCHEMA'.",
                fg="red",
            )
        )
        return False

    return True


def valid_source_dir(schema_name: str) -> bool:
    if not schema_name:
        click.echo(
            click.style(
                "CSV Source Directory not provided or found in the environment variable 'CSV_SOURCE_DIR'.",
                fg="red",
            )
        )
        return False

    return True
