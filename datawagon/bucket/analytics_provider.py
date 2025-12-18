"""Abstract analytics provider interface for multi-cloud support.

This module defines the AnalyticsProvider abstract base class that can be
implemented for different cloud analytics/data warehouse backends
(BigQuery, Redshift, Snowflake, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class AnalyticsProvider(ABC):
    """Abstract interface for analytics/data warehouse operations.

    Defines the contract for analytics operations that must be implemented
    by concrete providers (BigQuery, Redshift, Snowflake, etc.). Enables
    multi-cloud support without changing application logic.

    Example implementations:
        - BigQueryManager: Google BigQuery
        - RedshiftManager: AWS Redshift (future)
        - SnowflakeManager: Snowflake (future)
    """

    @abstractmethod
    def create_external_table(
        self,
        table_name: str,
        storage_folder_name: str,
        use_hive_partitioning: bool = True,
        schema: Optional[List[Any]] = None,
        use_autodetect_fallback: bool = True,
    ) -> bool:
        """Create external table referencing storage files.

        Args:
            table_name: Table name in analytics platform
            storage_folder_name: Storage folder path
            use_hive_partitioning: Enable Hive partitioning
            schema: Optional explicit schema (provider-specific type)
            use_autodetect_fallback: Fall back to auto-detection if schema fails

        Returns:
            True if creation succeeded, False otherwise
        """
        pass

    @abstractmethod
    def list_external_tables(self) -> List[Any]:
        """List all external tables in the dataset.

        Returns:
            List of table info objects (provider-specific type)
        """
        pass

    @abstractmethod
    def delete_table(self, table_name: str) -> bool:
        """Delete a table from the dataset.

        Args:
            table_name: Name of table to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        pass

    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the dataset.

        Args:
            table_name: Name of table to check

        Returns:
            True if table exists, False otherwise
        """
        pass

    @property
    @abstractmethod
    def has_error(self) -> bool:
        """Check if provider has encountered errors.

        Returns:
            True if provider is in error state, False otherwise

        Note:
            Read-only property to prevent external code from resetting error state.
        """
        pass

    @property
    @abstractmethod
    def dataset_id(self) -> str:
        """Get the analytics dataset/database name.

        Returns:
            Name of the dataset/database
        """
        pass
