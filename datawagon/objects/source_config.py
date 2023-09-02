# from dataclasses import field
import re
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel


class Source(BaseModel):
    is_enabled: bool
    file_name_base: str
    exclude_file_name_base: Optional[str] = None
    regex_pattern: Optional[re.Pattern] = None
    regex_group_names: Optional[List[str]] = None
    destination_table: str
    append_or_replace: str


class SourceConfig(BaseModel):
    title: str
    source: dict[str, Source]


class SourceFileAttributes(BaseModel):
    # TODO: merge with CsvFileInfoOverride
    file_name: str
    file_path: Path
    destination_table: str
    append_or_replace: Literal["append", "replace"]

    # allows for additional fields defined at runtime by regex_group_names
    class Config:
        extra = "allow"
