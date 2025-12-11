"""Source configuration models for file processing.

This module defines Pydantic models for configuring file sources, including
pattern matching, regex extraction, and destination settings. Includes security
validation for regex patterns to prevent ReDoS attacks.
"""

import re
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, field_validator, model_validator

from datawagon.security import SecurityError, validate_regex_complexity


class SourceFromLocalFS(BaseModel):
    """Configuration for processing files from local filesystem.

    Defines how to select, process, and route CSV files from a local directory
    to GCS. Includes regex pattern matching for metadata extraction and security
    validation to prevent ReDoS attacks.

    Attributes:
        is_enabled: Whether this file source is active
        storage_folder_name: GCS folder name for uploads (defaults to table_name if None)
        table_name: Destination table name
        select_file_name_base: Glob pattern to match files (e.g., "YouTube_*")
        exclude_file_name_base: Glob pattern to exclude files (e.g., ".~lock*")
        regex_pattern: Compiled regex for extracting metadata from filenames
        regex_group_names: Named groups from regex (e.g., ["content_owner", "file_date_key"])
        table_append_or_replace: Upload strategy ("append" or "replace")

    Example:
        >>> config = SourceFromLocalFS(
        ...     is_enabled=True,
        ...     select_file_name_base="YouTube_*_M_*",
        ...     exclude_file_name_base=".~lock*",
        ...     regex_pattern=r"YouTube_(.+)_M_(\\d{8})",
        ...     regex_group_names=["content_owner", "file_date_key"],
        ...     storage_folder_name="youtube_analytics",
        ...     table_name="youtube_raw",
        ...     table_append_or_replace="append"
        ... )
    """

    is_enabled: bool
    storage_folder_name: Optional[str] = None
    table_name: Optional[str] = None
    select_file_name_base: str
    exclude_file_name_base: Optional[str] = None
    regex_pattern: Optional[re.Pattern] = None
    regex_group_names: Optional[List[str]] = None
    table_append_or_replace: Literal["append", "replace"]

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
            raise ValueError(
                "regex_pattern and regex_group_names must both be set or both None"
            )

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
        file: Dictionary mapping source names to SourceFromLocalFS configurations

    Example:
        >>> config = SourceConfig(file={
        ...     "youtube": SourceFromLocalFS(...),
        ...     "tiktok": SourceFromLocalFS(...)
        ... })
    """

    file: dict[str, SourceFromLocalFS]
