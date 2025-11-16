"""Configuration models for data type inference and column processing."""

from typing import Dict, List

from pydantic import BaseModel, Field


class ColumnTypeMapping(BaseModel):
    """Configuration for mapping column name patterns to data types."""

    float_patterns: List[str] = Field(
        default=["revenue"],
        description="Column name patterns that should be treated as float64",
    )
    int_patterns: List[str] = Field(
        default=["view", "day", "date_key", "sec"],
        description="Column name patterns that should be treated as integers",
    )
    date_patterns: List[str] = Field(
        default=["date"],
        description="Column name patterns that should be treated as datetime64[ns]",
    )
    default_type: str = Field(
        default="object",
        description="Default data type for columns that don't match any pattern",
    )


class ColumnTransformConfig(BaseModel):
    """Configuration for column name transformations."""

    replacements: Dict[str, str] = Field(
        default={
            " ": "_",
            ".": "_",
            "-": "_",
            "/": "_",
            "(": "_",
            ")": "",
            "?": "",
            ":": "",
        },
        description="Character replacements for column name formatting",
    )
    to_lowercase: bool = Field(
        default=True, description="Whether to convert column names to lowercase"
    )


class DataProcessingConfig(BaseModel):
    """Complete configuration for data processing and type inference."""

    column_types: ColumnTypeMapping = Field(
        default_factory=ColumnTypeMapping,
        description="Configuration for data type inference",
    )
    column_transforms: ColumnTransformConfig = Field(
        default_factory=ColumnTransformConfig,
        description="Configuration for column name transformations",
    )
    metadata_columns: Dict[str, str] = Field(
        default={
            "_file_name": "file_name",
            "_content_owner": "content_owner",
            "_report_date_key": "report_date_key",
            "_file_load_date": "datetime.now(timezone.utc).replace(tzinfo=None)",
        },
        description="Metadata columns to add to processed data",
    )
