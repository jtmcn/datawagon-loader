from typing import List

from pydantic import BaseModel


class CurrentDestinationData(BaseModel):
    base_name: str
    file_count: int
    source_files: List[str]


class CurrentTableData(BaseModel):
    table_name: str
    total_rows: int
    file_count: int
    source_files: List[str]
