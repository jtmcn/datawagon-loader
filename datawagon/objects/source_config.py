import re
from typing import List, Literal, Optional

from pydantic import BaseModel


class SourceFromLocalFS(BaseModel):
    is_enabled: bool
    storage_folder_name: Optional[str] = None
    table_name: Optional[str] = None
    select_file_name_base: str
    exclude_file_name_base: Optional[str] = None
    regex_pattern: Optional[re.Pattern] = None
    regex_group_names: Optional[List[str]] = None
    table_append_or_replace: Literal["append", "replace"]


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
