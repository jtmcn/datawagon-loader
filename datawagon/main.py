import importlib.metadata

import click
import toml
from dotenv import find_dotenv, load_dotenv
from pydantic import ValidationError

from datawagon.commands.compare import compare_local_files_to_bucket
from datawagon.commands.file_zip_to_gzip import file_zip_to_gzip
from datawagon.commands.files_in_local_fs import files_in_local_fs
from datawagon.commands.files_in_storage import files_in_storage
from datawagon.commands.upload_to_storage import upload_all_gzip_csv
from datawagon.commands.validate_config import validate_config
from datawagon.logging_config import get_logger, setup_logging
from datawagon.objects.app_settings import AppSettings
from datawagon.objects.source_config import SourceConfig


@click.group(chain=True)
@click.pass_context
def cli(
    ctx: click.Context,
) -> None:
    """Datawagon CLI."""

    try:
        settings = AppSettings()
    except ValidationError as e:
        raise click.ClickException(f"Configuration validation failed:\n{e}")

    ctx.obj["CONFIG"] = settings
    ctx.obj["GLOBAL"] = {}

    logger = get_logger("main")
    logger.info(f"Loading source config from: {settings.csv_source_config}")

    try:
        source_config_file = toml.load(settings.csv_source_config)
        valid_config = SourceConfig(**source_config_file)
        logger.info(
            f"Successfully loaded configuration with {len(valid_config.file)} file sources"
        )

    except ValidationError as e:
        error_msg = (
            f"Configuration validation failed for {settings.csv_source_config}:\n{e}"
        )
        logger.error(error_msg)
        raise click.ClickException(error_msg)
    except FileNotFoundError:
        error_msg = f"Configuration file not found: {settings.csv_source_config}"
        logger.error(error_msg)
        raise click.ClickException(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error loading configuration: {e}"
        logger.error(error_msg)
        raise click.ClickException(error_msg)

    if not valid_config:
        error_msg = "Configuration validation resulted in empty config"
        logger.error(error_msg)
        raise click.ClickException(error_msg)

    ctx.obj["FILE_CONFIG"] = valid_config


cli.add_command(files_in_local_fs)
cli.add_command(compare_local_files_to_bucket)
cli.add_command(upload_all_gzip_csv)
cli.add_command(file_zip_to_gzip)
cli.add_command(files_in_storage)
cli.add_command(validate_config)


def start_cli() -> click.Group:
    # Set up logging first
    setup_logging(level="INFO")
    logger = get_logger("main")

    try:
        env_file = find_dotenv(usecwd=True, raise_error_if_not_found=True)
        load_dotenv(env_file, verbose=False)  # Reduce verbosity, use logging instead
        logger.info(f"Environment configuration loaded from: {env_file}")
    except OSError as e:
        logger.warning(f"No .env file found, using environment variables: {e}")
        # Continue execution as environment variables might be set directly
    except Exception as e:
        logger.error(f"Error loading environment configuration: {e}")
        raise click.ClickException(f"Failed to load environment configuration: {e}")

    click.secho("DataWagon", fg="magenta", bold=True)
    click.echo(f"Version: {importlib.metadata.version('datawagon')}")
    click.echo(nl=True)

    return cli(obj={})  # type: ignore


if __name__ == "__main__":
    start_cli()
