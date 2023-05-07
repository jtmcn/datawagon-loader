from abc import ABC, abstractmethod
from typing import List, Tuple


class DatabaseHandler(ABC):
    @abstractmethod
    def test_connection(self) -> bool:
        pass

    @abstractmethod
    def check_schema(self) -> bool:
        pass

    @abstractmethod
    def get_tables_and_row_counts(self, schema_name: str) -> List[Tuple[str, int]]:
        pass

    @abstractmethod
    def ensure_schema_exists(self) -> None:
        pass

    @abstractmethod
    def create_table_if_not_exists(self, table_name: str, header: List[str]) -> None:
        pass

    @abstractmethod
    def insert_data(
        self, table_name: str, header: List[str], data: List[List[str]]
    ) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def drop_all_tables_and_views(self) -> None:
        pass