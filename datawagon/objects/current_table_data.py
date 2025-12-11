"""Models for tracking current state of destination tables and data.

This module defines Pydantic models for representing the current state of
data in destination tables/buckets, including file counts and source files.
"""

from typing import List

from pydantic import BaseModel


class CurrentDestinationData(BaseModel):
    """Current state of destination data grouped by base_name.

    Attributes:
        base_name: File base name pattern
        file_count: Number of files with this base_name
        source_files: List of source file names
    """

    base_name: str
    file_count: int
    source_files: List[str]


class CurrentTableData(BaseModel):
    """Current state of a destination table.

    Attributes:
        table_name: Name of the destination table
        total_rows: Total number of rows in table
        file_count: Number of source files loaded
        source_files: List of source file names
    """

    table_name: str
    total_rows: int
    file_count: int
    source_files: List[str]
