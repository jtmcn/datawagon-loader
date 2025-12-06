import re
from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator

from datawagon.security import SecurityError, validate_regex_complexity


class SourceFromLocalFS(BaseModel):
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
    def validate_regex_pattern(cls, v):
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


class Destination(BaseModel):
    destination_type: Literal["table", "bucket"]


class DestinationAsBucket(BaseModel):
    destination_bucket: str
    partitions: Optional[List[str]] = None


class DestinationAsTable(BaseModel):
    destination_table: str
    append_or_replace: Literal["append", "replace"]


class SourceConfig(BaseModel):
    file: dict[str, SourceFromLocalFS]
