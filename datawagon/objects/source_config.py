"""Source configuration models for file processing.

This module defines Pydantic models for configuring file sources, including
pattern matching, regex extraction, and destination settings. Includes security
validation for regex patterns to prevent ReDoS attacks.
"""

import re
from typing import Any, List, Optional

from pydantic import BaseModel, field_validator, model_validator

from datawagon.security import SecurityError, validate_regex_complexity


class BigQueryConfig(BaseModel):
    """BigQuery configuration.

    Defines BigQuery dataset and storage settings for external table creation.

    Attributes:
        dataset: BigQuery dataset name for external tables
        storage_prefix: Deprecated; use the top-level ``storage_prefix``

    Example:
        >>> config = BigQueryConfig(dataset="youtube_analytics")
    """

    dataset: str
    storage_prefix: Optional[str] = None


class SourceFromLocalFS(BaseModel):
    """Configuration for processing files from local filesystem.

    Defines how to select, process, and route CSV files from a local directory
    to GCS. Includes regex pattern matching for metadata extraction and security
    validation to prevent ReDoS attacks.

    Attributes:
        is_enabled: Whether this file source is active
        storage_folder_name: Deprecated; derived from the Storage Prefix and Report Type
        table_name: Deprecated; derived from the Report Type and Version
        select_file_name_base: Pattern to match files (defaults to the section key)
        exclude_file_name_base: Glob pattern to exclude files (e.g., ".~lock*")
        regex_pattern: Compiled regex for extracting metadata from filenames
        regex_group_names: Named groups from regex (e.g., ["content_owner", "file_date_key"])

    Example:
        >>> config = SourceFromLocalFS(
        ...     is_enabled=True,
        ...     select_file_name_base="YouTube_*_M_*",
        ...     exclude_file_name_base=".~lock*",
        ...     regex_pattern=r"YouTube_(.+)_M_(\\d{8})",
        ...     regex_group_names=["content_owner", "file_date_key"],
        ... )
    """

    is_enabled: bool
    storage_folder_name: Optional[str] = None
    table_name: Optional[str] = None
    select_file_name_base: str
    exclude_file_name_base: Optional[str] = None
    regex_pattern: Optional[re.Pattern] = None
    regex_group_names: Optional[List[str]] = None

    @field_validator("regex_pattern", mode="before")
    @classmethod
    def validate_regex_pattern(cls, v: Any) -> Optional[re.Pattern]:
        """Validate regex pattern for security before compilation."""
        if v is None:
            return v

        # If already compiled, extract pattern string
        pattern_str = v.pattern if isinstance(v, re.Pattern) else str(v)

        try:
            validate_regex_complexity(pattern_str)
            # Test compilation
            return re.compile(pattern_str)
        except SecurityError as e:
            raise ValueError(f"Unsafe regex pattern: {e}")
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

    @model_validator(mode="after")
    def validate_regex_consistency(self) -> "SourceFromLocalFS":
        """Validate regex pattern and group names match at config load time."""
        # Both must be set or both None
        if (self.regex_pattern is None) != (self.regex_group_names is None):
            raise ValueError("regex_pattern and regex_group_names must both be set or both None")

        # FIX: Validate group count at config load time to catch errors early
        if self.regex_pattern and self.regex_group_names:
            num_groups = self.regex_pattern.groups
            expected_groups = len(self.regex_group_names)
            if num_groups != expected_groups:
                raise ValueError(
                    f"Regex pattern has {num_groups} groups but "
                    f"regex_group_names has {expected_groups} names. "
                    f"Pattern: {self.regex_pattern.pattern}, "
                    f"Names: {self.regex_group_names}"
                )

        return self


class SourceConfig(BaseModel):
    """Root configuration for all file sources.

    Container for multiple file source configurations, each identified by a unique
    name key. Loaded from source_config.toml.

    Attributes:
        storage_prefix: Bucket root for all Storage Folders (optional)
        file: Report Type (section key) to SourceFromLocalFS configuration
        bigquery: Optional BigQuery configuration

    Example:
        >>> config = SourceConfig(
        ...     file={
        ...         "youtube": SourceFromLocalFS(...),
        ...         "tiktok": SourceFromLocalFS(...)
        ...     },
        ...     bigquery=BigQueryConfig(dataset="youtube_analytics")
        ... )
    """

    storage_prefix: Optional[str] = None
    file: dict[str, SourceFromLocalFS]
    bigquery: Optional[BigQueryConfig] = None

    @model_validator(mode="before")
    @classmethod
    def default_select_file_name_base(cls, data: Any) -> Any:
        """A ``[file.X]`` section selects files containing ``X`` unless it says otherwise."""
        if isinstance(data, dict) and isinstance(data.get("file"), dict):
            for key, source in data["file"].items():
                if isinstance(source, dict):
                    source.setdefault("select_file_name_base", key)
        return data
