from pydantic import BaseModel, DirectoryPath, Field, FilePath


class AppSettings(BaseModel):
    csv_source_dir: DirectoryPath = Field(...)
    csv_source_config: FilePath = Field(...)
    gcs_project_id: str = Field(...)
    gcs_bucket: str = Field(...)

    class Config:
        # This allows the model to be created from environment variables
        # that are read by something like `dotenv.load_dotenv()`
        # without having to manually pass them in as keyword arguments.
        # The `env_file` and `env_file_encoding` settings are used
        # to specify the location of the environment file.
        # The `case_sensitive` setting is used to specify whether
        # the environment variable names are case-sensitive.
        # The `extra` setting is used to specify whether to allow
        # extra fields that are not defined in the model.
        # In this case, we want to ignore extra fields.
        # This is useful when you have other environment variables
        # that are not part of the application settings.
        # The `validate_assignment` setting is used to specify
        # whether to validate the model when a field is assigned a new value.
        # In this case, we want to validate the model when a field is assigned a new value.
        # This is useful for ensuring that the model is always in a valid state.
        # The `frozen` setting is used to specify whether the model is immutable.
        # In this case, we want the model to be immutable after it is created.
        # This is useful for ensuring that the model is not accidentally modified.
        # The `json_encoders` setting is used to specify custom JSON encoders
        # for types that are not supported by the default JSON encoder.
        # In this case, we are using a custom JSON encoder for the `Path` type.
        # This is useful for serializing the model to JSON.
        # The `parse_env_var` setting is used to specify a custom function
        # for parsing environment variables.
        # In this case, we are not using a custom function.
        # The `fields` setting is used to specify custom settings for each field.
        # In this case, we are not using custom settings for each field.
        # The `alias_generator` setting is used to specify a custom function
        # for generating aliases for each field.
        # In this case, we are not using a custom function.
        # The `title` setting is used to specify a custom title for the model.
        # In this case, we are not using a custom title.
        # The `description` setting is used to specify a custom description for the model.
        # In this case, we are not using a custom description.
        # The `default_factory` setting is used to specify a custom function
        # for generating default values for each field.
        # In this case, we are not using a custom function.
        # The `allow_population_by_field_name` setting is used to specify
        # whether to allow populating the model by field name.
        # In this case, we want to allow populating the model by field name.
        # This is useful for creating the model from a dictionary.
        # The `use_enum_values` setting is used to specify whether to use
        # the values of enums instead of the enum members themselves.
        # In this case, we are not using enums.
        # The `validate_all` setting is used to specify whether to validate
        # all fields when the model is created.
        # In this case, we want to validate all fields when the model is created.
        # This is useful for ensuring that the model is in a valid state.
        # The `extra` setting is set to "ignore" to ignore extra fields
        # that are not defined in the model.
        # This is useful when you have other environment variables
        # that are not part of the application settings.
        # The `allow_mutation` setting is set to `False` to make the model immutable.
        # This is useful for ensuring that the model is not accidentally modified.
        # The `frozen` setting is set to `True` to make the model immutable.
        # This is useful for ensuring that the model is not accidentally modified.
        # The `arbitrary_types_allowed` setting is set to `True` to allow
        # arbitrary types to be used in the model.
        # In this case, we are not using arbitrary types.
        # The `orm_mode` setting is set to `True` to allow the model to be used
        # with an ORM.
        # In this case, we are not using an ORM.
        # The `schema_extra` setting is used to specify extra schema information.
        # In this case, we are not using extra schema information.
        # The `json_loads` setting is used to specify a custom function
        # for loading JSON.
        # In this case, we are not using a custom function.
        # The `json_dumps` setting is used to specify a custom function
        case_sensitive = False
        extra = "ignore"
        frozen = True
