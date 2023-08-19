from typing import List

from pydantic import BaseModel


class CurrentTableData(BaseModel):
    table_name: str
    total_rows: int
    file_count: int
    source_files: List[str]
