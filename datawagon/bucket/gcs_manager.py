import os
from typing import List

import pandas as pd
from google.api_core import exceptions as google_api_exceptions
from google.cloud import storage

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
    def __init__(self, gcs_project: str, source_bucket_name: str) -> None:
        self.storage_client = storage.Client(project=gcs_project)
        self.source_bucket_name = source_bucket_name
        try:
            existing_buckets = self.storage_client.list_buckets()
            for bucket in existing_buckets:
                logger.info(f"Found GCS bucket: {bucket.name}")
            self.has_error = False
        except google_api_exceptions.Unauthenticated as e:
            logger.error(f"GCS authentication failed: {e}")
            logger.error(
                "Authentication required. Run: gcloud auth application-default login"
            )
            self.has_error = True
        except google_api_exceptions.PermissionDenied as e:
            logger.error(f"GCS permission denied: {e}")
            self.has_error = True
        except Exception as e:
            logger.error(f"Error connecting to GCS: {e}", exc_info=True)
            self.has_error = True
        
    def list_buckets(self) -> List[str]:
        buckets = self.storage_client.list_buckets()
        return [bucket.name for bucket in buckets]

    @retry_with_backoff(retries=3, exceptions=TRANSIENT_EXCEPTIONS)
    def list_blobs(
        self, storage_folder_name: str, file_name_base: str, file_extension: str
    ) -> List[str]:
        """List blobs matching pattern in both versioned and non-versioned folders."""
        if not self.has_error:
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
            except google_api_exceptions.NotFound as e:
                logger.error(f"Bucket not found: {e}")
            except google_api_exceptions.PermissionDenied as e:
                logger.error(f"Permission denied listing blobs: {e}")
            except Exception as e:
                logger.error(f"Unable to list files in bucket: {e}", exc_info=True)
        return []

    def files_in_blobs_df(self, source_confg: SourceConfig) -> pd.DataFrame:
        combined_df = pd.DataFrame(columns=["_file_name", "base_name"])

        for file_id in source_confg.file:
            file_source = source_confg.file[file_id]
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

    @retry_with_backoff(retries=3, exceptions=TRANSIENT_EXCEPTIONS)
    def upload_blob(self, source_file_name: str, destination_blob_name: str) -> bool:
        # Validate blob name for security
        try:
            validated_destination = validate_blob_name(destination_blob_name)
        except SecurityError as e:
            logger.error(f"Invalid blob name: {e}")
            raise ValueError(f"Invalid destination blob name: {e}")

        try:
            bucket = self.storage_client.bucket(self.source_bucket_name)
            blob = bucket.blob(validated_destination)
            blob.upload_from_filename(source_file_name)
            return True
        except google_api_exceptions.PermissionDenied as e:
            logger.error(f"Permission denied uploading to bucket: {e}")
            return False
        except google_api_exceptions.NotFound as e:
            logger.error(f"Bucket not found: {e}")
            return False
        except Exception as e:
            logger.error(f"Unable to upload file to bucket: {e}", exc_info=True)
            return False

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

    @retry_with_backoff(retries=3, exceptions=TRANSIENT_EXCEPTIONS)
    def copy_blob_within_bucket(
        self, source_blob_name: str, destination_blob_name: str
    ) -> bool:
        """Copy a blob to a new location within the same bucket."""
        if not self.has_error:
            try:
                bucket = self.storage_client.bucket(self.source_bucket_name)
                source_blob = bucket.blob(source_blob_name)

                # Copy blob within same bucket
                destination_blob = bucket.copy_blob(
                    source_blob, bucket, destination_blob_name
                )

                # Verify copy succeeded
                if destination_blob.exists():
                    return True
                else:
                    logger.error(
                        f"Copy verification failed for {destination_blob_name}"
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
                blobs = self.storage_client.list_blobs(
                    self.source_bucket_name, prefix=prefix
                )
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
