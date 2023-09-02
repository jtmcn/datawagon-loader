from pathlib import Path

import click


class ParameterValidator(object):
    def __init__(
        self, db_url: str, schema_name: str, dir_name: Path, config_file: Path
    ) -> None:
        self.are_valid_parameters = (
            self.is_valid_url(db_url)
            and self.is_valid_schema(schema_name)
            and self.is_valid_source_dir(dir_name)
            and self.is_vaild_config_location(config_file)
        )

    def is_valid_url(self, db_url: str) -> bool:
        if not db_url:
            click.secho(
                "Database URL not provided or found in the environment variable 'DW_POSTGRES_DB_URL'.",
                fg="red",
            )
            return False
        return True

    def is_valid_schema(self, schema_name: str) -> bool:
        if not schema_name:
            click.secho(
                "Schema not provided or found in the environment variable 'DW_DB_SCHEMA'.",
                fg="red",
            )
            return False
        if not self.is_sql_safe(schema_name):
            click.style(
                f"Invalid schema name: {schema_name}. Contains potentially unsafe characters or keywords.",
                fg="red",
            )
            return False
        return True

    def is_sql_safe(self, param: str) -> bool:
        """
        Check if the SQL parameter contains potentially harmful characters or keywords
        """
        param_lower = param.lower()

        sql_keywords = [
            "select",
            "drop",
            "update",
            "delete",
            "truncate",
            "insert",
            ";",
            "--",
            "exec",
            "declare",
            "create",
            "alter",
        ]

        for keyword in sql_keywords:
            if keyword in param_lower:
                return False

        special_characters = [
            "'",
            '"',
            ";",
            "--",
            "/*",
            "*/",
            "@@",
            "@",
            "char",
            "nchar",
            "varchar",
            "nvarchar",
            "+",
            "exec",
            "0x",
        ]
        for special_character in special_characters:
            if special_character in param_lower:
                return False

        return True

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
