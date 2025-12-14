"""Google Cloud Storage bucket management.

This module provides the GcsManager class for interacting with GCS buckets,
including uploading files, listing blobs, copying blobs, and managing blob
metadata. Includes retry logic for transient failures and security validation.
"""

import os
import time
from pathlib import Path
from typing import List

import pandas as pd
from google.api_core import exceptions as google_api_exceptions
from google.cloud import storage  # type: ignore[attr-defined]

from datawagon.bucket.retry_utils import retry_with_backoff
from datawagon.logging_config import get_logger
from datawagon.objects.source_config import SourceConfig
from datawagon.security import SecurityError, validate_blob_name

logger = get_logger(__name__)

# GCS transient failures that should be retried
TRANSIENT_EXCEPTIONS = (
    google_api_exceptions.ServiceUnavailable,  # 503
    google_api_exceptions.DeadlineExceeded,  # 504
    google_api_exceptions.InternalServerError,  # 500
    google_api_exceptions.TooManyRequests,  # 429 rate limiting
)


class GcsManager:
    """Manager for Google Cloud Storage bucket operations.

    Provides high-level interface for GCS operations including file uploads,
    blob listing, and blob copying. Includes automatic retry logic for transient
    failures and security validation for blob names.

    Attributes:
        storage_client: GCS storage client
        source_bucket_name: Name of the GCS bucket to operate on
        has_error: Flag indicating if initialization encountered errors
    """

    def __init__(self, gcs_project: str, source_bucket_name: str) -> None:
        """Initialize GCS manager and verify access.

        Creates GCS client, lists available buckets to verify authentication,
        and sets error flag if connection fails.

        Args:
            gcs_project: GCP project ID
            source_bucket_name: Name of GCS bucket to use

        Note:
            Sets has_error=True if authentication or permissions fail.
            Run 'gcloud auth application-default login' if authentication fails.
        """
        self.storage_client = storage.Client(project=gcs_project)
        self.source_bucket_name = source_bucket_name
        try:
            existing_buckets = self.storage_client.list_buckets()
            for bucket in existing_buckets:
                logger.info(f"Found GCS bucket: {bucket.name}")
            self.has_error = False
        except google_api_exceptions.Unauthenticated as e:
            logger.error(f"GCS authentication failed: {e}")
            logger.error("Authentication required. Run: gcloud auth application-default login")
            self.has_error = True
        except google_api_exceptions.PermissionDenied as e:
            logger.error(f"GCS permission denied: {e}")
            self.has_error = True
        except Exception as e:
            logger.error(f"Error connecting to GCS: {e}", exc_info=True)
            self.has_error = True

    def list_buckets(self) -> List[str]:
        """List all accessible GCS buckets in the project.

        Returns:
            List of bucket names
        """
        buckets = self.storage_client.list_buckets()
        return [bucket.name for bucket in buckets]

    @retry_with_backoff(retries=3, exceptions=TRANSIENT_EXCEPTIONS)
    def list_blobs(self, storage_folder_name: str, file_name_base: str, file_extension: str) -> List[str]:
        """List blobs matching pattern with proper error propagation."""
        if self.has_error:
            logger.error("GCS client has errors, cannot list blobs")
            return []

        try:
            # Extract parent directory for efficient search
            if "/" in storage_folder_name:
                parts = storage_folder_name.rsplit("/", 1)
                parent_prefix = parts[0] + "/"
                folder_base = parts[1]
            else:
                parent_prefix = ""
                folder_base = storage_folder_name

            # Search with glob that matches both:
            # - caravan/claim_raw/report_date=*/file.csv.gz
            # - caravan/claim_raw_v1-0/report_date=*/file.csv.gz
            blobs = self.storage_client.list_blobs(
                self.source_bucket_name,
                prefix=parent_prefix,
                match_glob=f"**{folder_base}*/**{file_name_base}**{file_extension}",
            )
            return [blob.name for blob in blobs]

        except google_api_exceptions.NotFound:
            # Bucket not found - return empty (expected case)
            logger.warning(f"Bucket not found: {self.source_bucket_name}")
            return []

        except (
            google_api_exceptions.Unauthenticated,
            google_api_exceptions.PermissionDenied,
        ) as e:
            # FIX: Auth/permission errors should be fatal, not silent
            logger.error(f"GCS access error: {e}. Run: gcloud auth application-default login")
            self.has_error = True
            raise  # Re-raise to signal caller

        except Exception as e:
            # Other errors - log with full trace and return empty
            logger.error(f"Unable to list files in bucket: {e}", exc_info=True)
            return []

    def files_in_blobs_df(self, source_confg: SourceConfig) -> pd.DataFrame:
        """Get DataFrame of files in bucket for all enabled sources.

        Lists files in bucket matching each enabled source configuration and
        combines into a single DataFrame.

        Args:
            source_confg: Source configuration with enabled file sources

        Returns:
            DataFrame with columns: _file_name, base_name

        Example:
            >>> df = manager.files_in_blobs_df(config)
            >>> df.head()
               _file_name             base_name
            0  file1.csv.gz           YouTube_*
            1  file2.csv.gz           YouTube_*
        """
        combined_df = pd.DataFrame(columns=["_file_name", "base_name"])

        for file_id in source_confg.file:
            file_source = source_confg.file[file_id]
            if file_source.is_enabled:
                blob_list = self.list_blobs(
                    file_source.storage_folder_name or file_source.select_file_name_base,
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

                # FIX: Reset index to prevent duplicate indices after concat
                combined_df = pd.concat([combined_df, df], ignore_index=True)

        return combined_df

    @retry_with_backoff(retries=3, exceptions=TRANSIENT_EXCEPTIONS)
    def upload_blob(self, source_file_name: str, destination_blob_name: str, overwrite: bool = False) -> bool:
        """Upload file to GCS bucket with retry logic and race condition protection.

        Validates blob name for security, then uploads file to GCS with automatic
        retry for transient failures (503, 504, 500, 429). Uses atomic operations
        to prevent race conditions when overwrite=False.

        Args:
            source_file_name: Local file path to upload
            destination_blob_name: Destination path in GCS bucket
            overwrite: If False, fails if blob already exists (prevents races)

        Returns:
            True if upload succeeded, False otherwise

        Raises:
            ValueError: If destination blob name is invalid

        Example:
            >>> manager.upload_blob("/data/file.csv.gz", "youtube/report_date=2023-06-30/file.csv.gz")
            True
        """
        # Get file size for metrics
        file_path = Path(source_file_name)
        file_size_bytes = file_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Start timing
        start_time = time.perf_counter()

        # Validate blob name for security
        try:
            validated_destination = validate_blob_name(destination_blob_name)
        except SecurityError as e:
            logger.error(f"Invalid blob name: {e}")
            raise ValueError(f"Invalid destination blob name: {e}")

        try:
            bucket = self.storage_client.bucket(self.source_bucket_name)
            blob = bucket.blob(validated_destination)

            # FIX: Use atomic create-if-not-exists to prevent race conditions
            # if_generation_match=0 means only succeed if blob doesn't exist
            generation_match = None if overwrite else 0

            blob.upload_from_filename(source_file_name, if_generation_match=generation_match)

            # Calculate metrics
            duration = time.perf_counter() - start_time
            throughput = file_size_mb / duration if duration > 0 else 0

            logger.info(
                f"Uploaded: {os.path.basename(destination_blob_name)} "
                f"({file_size_mb:.2f} MB in {duration:.2f}s, {throughput:.2f} MB/s)"
            )
            return True
        except google_api_exceptions.PreconditionFailed:
            duration = time.perf_counter() - start_time
            logger.warning(f"Blob already exists (checked in {duration:.2f}s), skipping: {destination_blob_name}")
            return False
        except google_api_exceptions.PermissionDenied as e:
            duration = time.perf_counter() - start_time
            logger.error(f"Permission denied after {duration:.2f}s uploading to bucket: {e}")
            return False
        except google_api_exceptions.NotFound as e:
            duration = time.perf_counter() - start_time
            logger.error(f"Bucket not found after {duration:.2f}s: {e}")
            return False
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(f"Unable to upload file after {duration:.2f}s to bucket: {e}", exc_info=True)
            return False

    # 10/2/23 - all four of these functions are currently unused
    def delete_blob(self, blob_name: str) -> None:
        """Delete a blob from the bucket.

        Args:
            blob_name: Name of blob to delete
        """
        bucket = self.storage_client.bucket(self.source_bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()

    def get_blob_metadata(self, blob_name: str) -> dict | None:
        """Get metadata for a specific blob.

        Args:
            blob_name: Name of blob to get metadata for

        Returns:
            Dictionary of blob metadata, or None if blob doesn't exist
        """
        blob = self.get_blob(blob_name)
        return blob.metadata

    def get_blob(self, blob_name: str) -> storage.Blob:
        """Get blob object by name.

        Args:
            blob_name: Name of blob to retrieve

        Returns:
            storage.Blob object
        """
        bucket = self.storage_client.bucket(self.source_bucket_name)
        blob = bucket.blob(blob_name)
        return blob

    def download_blob(self, blob_name: str, destination_file_name: str) -> None:
        """Download blob to local file.

        Args:
            blob_name: Name of blob to download
            destination_file_name: Local path to save downloaded file
        """
        blob = self.get_blob(blob_name)
        blob.download_to_filename(destination_file_name)

    @retry_with_backoff(retries=3, exceptions=TRANSIENT_EXCEPTIONS)
    def copy_blob_within_bucket(self, source_blob_name: str, destination_blob_name: str) -> bool:
        """Copy a blob to a new location within the same bucket with atomic verification."""
        if not self.has_error:
            try:
                # Validate destination path before attempting copy
                try:
                    validate_blob_name(destination_blob_name)
                except SecurityError as e:
                    logger.error(f"Invalid destination blob name: {e}")
                    return False

                # Log the copy operation
                logger.info(f"Attempting copy: {source_blob_name} -> {destination_blob_name}")

                bucket = self.storage_client.bucket(self.source_bucket_name)
                source_blob = bucket.blob(source_blob_name)

                # Fetch source blob metadata from GCS (required for size comparison)
                source_blob.reload()
                logger.debug(f"Source blob size: {source_blob.size} bytes")

                # Copy blob within same bucket - returns new blob with metadata
                destination_blob = bucket.copy_blob(source_blob, bucket, destination_blob_name)

                # Reload destination blob to get fresh metadata from GCS
                destination_blob.reload()
                logger.debug(f"Destination blob created with size: {destination_blob.size} bytes")

                # FIX: Verify immediately using returned object (no TOCTOU gap)
                # Compare sizes to ensure copy completed successfully
                if destination_blob.size == source_blob.size:
                    logger.info(
                        f"Copied: {source_blob_name} -> {destination_blob_name} " f"({destination_blob.size} bytes)"
                    )
                    return True
                else:
                    logger.error(
                        f"Size mismatch: source={source_blob_name} "
                        f"({source_blob.size}B) dest={destination_blob_name} "
                        f"({destination_blob.size}B)"
                    )
                    return False

            except google_api_exceptions.NotFound as e:
                logger.error(f"Source blob not found: {e}")
                return False
            except google_api_exceptions.PermissionDenied as e:
                logger.error(f"Permission denied copying blob: {e}")
                return False
            except Exception as e:
                logger.error(f"Error copying blob: {e}", exc_info=True)
                return False
        return False

    @retry_with_backoff(retries=3, exceptions=TRANSIENT_EXCEPTIONS)
    def list_all_blobs_with_prefix(self, prefix: str = "") -> List[str]:
        """List all blobs in bucket with given prefix."""
        if not self.has_error:
            try:
                blobs = self.storage_client.list_blobs(self.source_bucket_name, prefix=prefix)
                return [blob.name for blob in blobs]
            except google_api_exceptions.NotFound as e:
                logger.error(f"Bucket not found: {e}")
                return []
            except google_api_exceptions.PermissionDenied as e:
                logger.error(f"Permission denied listing blobs: {e}")
                return []
            except Exception as e:
                logger.error(f"Error listing blobs: {e}", exc_info=True)
                return []
        return []
