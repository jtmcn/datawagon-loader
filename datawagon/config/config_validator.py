"""
class ConfigValidator:

    def __init__(self, config_file_location: Path) -> None:
        self.app_config = app_config

        try:
            source_config_file = toml.load(app_config.csv_source_config)
            self.valid_config = SourceConfig(**source_config_file)

        except ValidationError as e:
            raise ValueError(f"Validation Failed for source_config.toml\n{e}
"""
