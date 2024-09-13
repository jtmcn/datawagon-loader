from pathlib import Path

import click


class ParameterValidator(object):
    def __init__(self, dir_name: Path, config_file: Path) -> None:
        self.are_valid_parameters = self.is_valid_source_dir(
            dir_name
        ) and self.is_vaild_config_location(config_file)

    def is_valid_source_dir(self, dir_name: Path) -> bool:
        if not dir_name:
            click.secho(
                "CSV Source Directory not provided or found in the environment variable 'CSV_SOURCE_DIR'.",
                fg="red",
            )
            return False
        return True

    def is_vaild_config_location(self, config_file: Path) -> bool:
        if not config_file:
            click.secho(
                "CSV Source Config (source_config.toml) "
                + "file not found in the environment variable 'DW_CSV_SOURCE_TOML'.",
                fg="red",
            )
            return False
        return True
