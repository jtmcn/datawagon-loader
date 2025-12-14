"""Abstract storage provider interface for multi-cloud support.

This module defines the StorageProvider abstract base class that can be
implemented for different cloud storage backends (GCS, S3, Azure Blob, etc.).
"""

from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any, List


class StorageProvider(ABC):
    """Abstract interface for cloud storage operations.

    Defines the contract for storage operations that must be implemented
    by concrete providers (GCS, S3, Azure, etc.). Enables multi-cloud
    support without changing application logic.

    Example implementations:
        - GcsManager: Google Cloud Storage
        - S3Manager: AWS S3 (future)
        - AzureBlobManager: Azure Blob Storage (future)
    """

    @abstractmethod
    def upload_blob(self, source_file_name: str, destination_blob_name: str, overwrite: bool = False) -> bool:
        """Upload file to storage bucket.

        Args:
            source_file_name: Local file path to upload
            destination_blob_name: Destination path in storage
            overwrite: If False, fails if blob already exists

        Returns:
            True if upload succeeded, False otherwise
        """
        pass

    @abstractmethod
    def list_blobs(self, storage_folder_name: str, file_name_base: str, file_extension: str) -> List[str]:
        """List blobs matching pattern in storage folder.

        Args:
            storage_folder_name: Storage folder path
            file_name_base: Base filename pattern to match
            file_extension: File extension to match (e.g., ".csv.gz")

        Returns:
            List of blob names matching the pattern
        """
        pass

    @abstractmethod
    def list_all_blobs_with_prefix(self, prefix: str = "") -> List[str]:
        """List all blobs with given prefix.

        Args:
            prefix: Path prefix to filter blobs

        Returns:
            List of all blob names with the prefix
        """
        pass

    @abstractmethod
    def get_blob(self, blob_name: str) -> Any:
        """Get blob object by name.

        Args:
            blob_name: Name of blob to retrieve

        Returns:
            Blob object (type depends on provider implementation)
        """
        pass

    @abstractmethod
    def copy_blob_within_bucket(self, source_blob_name: str, destination_blob_name: str) -> bool:
        """Copy blob to new location within same bucket.

        Args:
            source_blob_name: Source blob path
            destination_blob_name: Destination blob path

        Returns:
            True if copy succeeded, False otherwise
        """
        pass

    @abstractmethod
    def read_blob_to_memory(self, blob_name: str) -> BytesIO:
        """Read blob contents into memory.

        Args:
            blob_name: Name of blob to read

        Returns:
            BytesIO object containing blob data
        """
        pass

    @property
    @abstractmethod
    def has_error(self) -> bool:
        """Check if provider has encountered errors.

        Returns:
            True if provider is in error state, False otherwise
        """
        pass

    @has_error.setter
    @abstractmethod
    def has_error(self, value: bool) -> None:
        """Set the error state of the provider.

        Args:
            value: True to mark provider as in error state, False otherwise
        """
        pass

    @property
    @abstractmethod
    def bucket_name(self) -> str:
        """Get the storage bucket name.

        Returns:
            Name of the storage bucket
        """
        pass
