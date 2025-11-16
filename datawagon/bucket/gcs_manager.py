import os
from typing import List

import pandas as pd
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

from datawagon.exceptions import GcsConnectionError, GcsOperationError
from datawagon.logging_config import get_logger
from datawagon.objects.source_config import SourceConfig
from datawagon.utils.retry import retry_with_exponential_backoff


class GcsManager:
    """Manages interactions with Google Cloud Storage.

    Provides methods for listing, uploading, and downloading files from GCS buckets.
    Includes error handling and logging for all operations.
    """

    def __init__(self, gcs_project: str, source_bucket_name: str) -> None:
        """Initialize the GCS manager.

        Args:
            gcs_project: Google Cloud project ID
            source_bucket_name: Name of the GCS bucket to use

        Raises:
            GcsConnectionError: If unable to connect to Google Cloud Storage
        """
        self.logger = get_logger("gcs_manager")
        self.storage_client = storage.Client(project=gcs_project)
        self.source_bucket_name = source_bucket_name
        try:
            existing_buckets = self.storage_client.list_buckets()
            bucket_names = [bucket.name for bucket in existing_buckets]
            self.logger.info(f"Connected to GCS, found {len(bucket_names)} buckets")
            self.logger.debug(f"Available buckets: {bucket_names}")
            self.has_error = False
        except GoogleCloudError as e:
            self.logger.error(f"Google Cloud error connecting to GCS: {e}")
            self.logger.error(
                "Make sure you're logged-in: gcloud auth application-default login"
            )
            self.has_error = True
            raise GcsConnectionError(
                f"Failed to connect to Google Cloud Storage: {e}"
            ) from e
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to GCS: {e}")
            self.has_error = True
            raise GcsConnectionError(f"Unexpected error connecting to GCS: {e}") from e

    def list_buckets(self) -> List[str]:
        """List all available buckets in the project.

        Returns:
            List of bucket names
        """
        buckets = self.storage_client.list_buckets()
        return [bucket.name for bucket in buckets]

    @retry_with_exponential_backoff(
        max_retries=3, base_delay=1.0, exceptions=(GoogleCloudError,)
    )
    def list_blobs(
        self, storage_folder_name: str, file_name_base: str, file_extension: str
    ) -> List[str]:
        """List blobs in the bucket matching the specified pattern.

        Args:
            storage_folder_name: Prefix path in the bucket
            file_name_base: Base name pattern to match
            file_extension: File extension to match

        Returns:
            List of blob names matching the pattern

        Raises:
            GcsConnectionError: If GCS connection is in error state
            GcsOperationError: If the list operation fails
        """
        if self.has_error:
            raise GcsConnectionError("GCS connection is in error state")

        try:
            blobs = self.storage_client.list_blobs(
                self.source_bucket_name,
                prefix=storage_folder_name + "/",
                match_glob="**" + file_name_base + "**" + file_extension,
            )
            return [blob.name for blob in blobs]
        except GoogleCloudError as e:
            self.logger.error(f"Google Cloud error listing files in bucket: {e}")
            raise GcsOperationError(f"Failed to list files in bucket: {e}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error listing files in bucket: {e}")
            raise GcsOperationError(f"Unexpected error listing files: {e}") from e

    def files_in_blobs_df(self, source_config: SourceConfig) -> pd.DataFrame:
        """Create a DataFrame of files in the bucket based on source configuration.

        Args:
            source_config: Configuration specifying which files to include

        Returns:
            DataFrame with file names and base names
        """
        combined_df = pd.DataFrame(columns=["_file_name", "base_name"])

        for file_id in source_config.file:
            file_source = source_config.file[file_id]
            if file_source.is_enabled:
                blob_list = self.list_blobs(
                    file_source.storage_folder_name
                    or file_source.select_file_name_base,
                    file_source.select_file_name_base,
                    ".csv.gz",
                )

                file_list = []
                for blob in blob_list:
                    # remove the base_prefix and file_extension from the blob name
                    # to prevent duplicate files
                    file_list.append(os.path.basename(blob))

                df = pd.DataFrame(file_list, columns=["_file_name"])
                df["base_name"] = file_source.select_file_name_base

                combined_df = pd.concat([combined_df, df])

        return combined_df

    @retry_with_exponential_backoff(
        max_retries=3, base_delay=2.0, exceptions=(GoogleCloudError,)
    )
    def upload_blob(self, source_file_name: str, destination_blob_name: str) -> bool:
        """Upload a file to the GCS bucket.

        Args:
            source_file_name: Path to the local file to upload
            destination_blob_name: Name for the blob in the bucket

        Returns:
            True if upload was successful

        Raises:
            GcsConnectionError: If GCS connection is in error state
            GcsOperationError: If the upload operation fails
        """
        if self.has_error:
            raise GcsConnectionError("GCS connection is in error state")

        try:
            bucket = self.storage_client.bucket(self.source_bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file_name)
            self.logger.info(
                f"Successfully uploaded '{source_file_name}' to '{destination_blob_name}'"
            )
            return True
        except GoogleCloudError as e:
            self.logger.error(
                f"Google Cloud error uploading file '{source_file_name}': {e}"
            )
            raise GcsOperationError(
                f"Failed to upload file '{source_file_name}': {e}"
            ) from e
        except FileNotFoundError as e:
            self.logger.error(f"Source file not found: '{source_file_name}'")
            raise GcsOperationError(
                f"Source file not found: '{source_file_name}'"
            ) from e
        except Exception as e:
            self.logger.error(
                f"Unexpected error uploading file '{source_file_name}': {e}"
            )
            raise GcsOperationError(f"Unexpected error uploading file: {e}") from e

    # 10/2/23 - all four of these functions are currently unused
    def delete_blob(self, blob_name: str) -> None:
        bucket = self.storage_client.bucket(self.source_bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()

    def get_blob_metadata(self, blob_name: str) -> dict | None:
        blob = self.get_blob(blob_name)
        return blob.metadata

    def get_blob(self, blob_name: str) -> storage.Blob:
        bucket = self.storage_client.bucket(self.source_bucket_name)
        blob = bucket.blob(blob_name)
        return blob

    def download_blob(self, blob_name: str, destination_file_name: str) -> None:
        blob = self.get_blob(blob_name)
        blob.download_to_filename(destination_file_name)
