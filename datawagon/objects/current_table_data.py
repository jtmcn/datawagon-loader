from dataclasses import dataclass
from typing import List


# TODO: use pydantic instead of dataclasses
@dataclass
class CurrentTableData:
    table_name: str
    total_rows: int
    file_count: int
    source_files: List[str]
