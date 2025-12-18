"""Google BigQuery external table management.

This module provides the BigQueryManager class for managing BigQuery external
tables that reference CSV files in GCS. Includes table creation with Hive
partitioning, listing tables, and schema auto-detection.
"""

import re
from typing import List, Optional

from google.api_core import exceptions as google_api_exceptions
from google.cloud import bigquery, storage

from datawagon.bucket.analytics_provider import AnalyticsProvider
from datawagon.bucket.retry_utils import retry_with_backoff
from datawagon.logging_config import get_logger
from datawagon.objects.bigquery_table_metadata import BigQueryTableInfo

logger = get_logger(__name__)

# BigQuery transient failures that should be retried
TRANSIENT_EXCEPTIONS = (
    google_api_exceptions.ServiceUnavailable,  # 503
    google_api_exceptions.DeadlineExceeded,  # 504
    google_api_exceptions.InternalServerError,  # 500
    google_api_exceptions.TooManyRequests,  # 429 rate limiting
)


class BigQueryManager(AnalyticsProvider):
    """Google BigQuery implementation of AnalyticsProvider.

    Provides high-level interface for creating and managing BigQuery external
    tables that reference CSV files in GCS. Includes automatic retry logic for
    transient failures and table name validation.

    Attributes:
        bq_client: BigQuery client
        project_id: GCP project ID
        _dataset_id: BigQuery dataset name (private, accessed via property)
        bucket_name: GCS bucket name for source URIs
        _has_error: Flag indicating if initialization encountered errors (private)
    """

    def __init__(self, project_id: str, dataset_id: str, bucket_name: str) -> None:
        """Initialize BigQuery manager and verify dataset access.

        Creates BigQuery client, verifies dataset exists and is accessible,
        and sets error flag if connection fails.

        Args:
            project_id: GCP project ID
            dataset_id: BigQuery dataset name
            bucket_name: GCS bucket name (for constructing source URIs)

        Note:
            Sets has_error=True if authentication or permissions fail.
            Run 'gcloud auth application-default login' if authentication fails.
        """
        self.bq_client = bigquery.Client(project=project_id)
        self.storage_client = storage.Client(project=project_id)
        self.project_id = project_id
        self._dataset_id = dataset_id
        self.bucket_name = bucket_name
        self._has_error = False

        try:
            # Verify dataset exists and is accessible
            dataset_ref = f"{project_id}.{dataset_id}"
            dataset = self.bq_client.get_dataset(dataset_ref)
            logger.info(f"Found BigQuery dataset: {dataset.dataset_id}")
        except google_api_exceptions.Unauthenticated as e:
            logger.error(f"BigQuery authentication failed: {e}")
            logger.error("Authentication required. Run: gcloud auth application-default login")
            self._has_error = True
        except google_api_exceptions.NotFound:
            logger.error(f"BigQuery dataset not found: {dataset_id}")
            logger.error(f"Create dataset with: bq mk --dataset {project_id}:{dataset_id}")
            self._has_error = True
        except google_api_exceptions.PermissionDenied as e:
            logger.error(f"BigQuery permission denied: {e}")
            self._has_error = True
        except Exception as e:
            logger.error(f"Error connecting to BigQuery: {e}", exc_info=True)
            self._has_error = True

    @staticmethod
    def normalize_table_name(table_name: str, file_version: str) -> str:
        """Convert table name and version to BigQuery-compatible format.

        BigQuery table names must use underscores, not hyphens.
        Converts "claim_raw" + "v1-1" → "claim_raw_v1_1"

        Args:
            table_name: Base table name (e.g., "claim_raw")
            file_version: Version string (e.g., "v1-1" or empty)

        Returns:
            BigQuery-compatible table name

        Example:
            >>> BigQueryManager.normalize_table_name("claim_raw", "v1-1")
            'claim_raw_v1_1'
            >>> BigQueryManager.normalize_table_name("asset_raw", "")
            'asset_raw'
        """
        if file_version:
            # Replace hyphens with underscores for BigQuery compatibility
            bq_version = file_version.replace("-", "_")
            return f"{table_name}_{bq_version}"
        return table_name

    @retry_with_backoff(retries=3, exceptions=TRANSIENT_EXCEPTIONS)
    def list_external_tables(self) -> List[BigQueryTableInfo]:
        """List all external tables in the dataset.

        Returns:
            List of BigQueryTableInfo for external tables only

        Example:
            >>> manager.list_external_tables()
            [BigQueryTableInfo(table_name='claim_raw_v1_1', ...)]
        """
        if self._has_error:
            return []

        try:
            dataset_ref = f"{self.project_id}.{self._dataset_id}"
            tables = self.bq_client.list_tables(dataset_ref)

            external_tables = []
            for table_item in tables:
                # Get full table metadata
                table = self.bq_client.get_table(table_item.reference)

                # Only include external tables
                if table.external_data_configuration:
                    ext_config = table.external_data_configuration

                    # Extract partition info
                    is_partitioned = False
                    partition_columns = None
                    if ext_config.hive_partitioning:
                        is_partitioned = True
                        # Extract partition columns from source URI pattern
                        if ext_config.source_uris:
                            partition_columns = self._extract_partition_columns(ext_config.source_uris[0])

                    # Construct source URI pattern
                    source_uri_pattern = ext_config.source_uris[0] if ext_config.source_uris else ""

                    table_info = BigQueryTableInfo(
                        table_name=table.table_id,
                        dataset_id=self._dataset_id,
                        project_id=self.project_id,
                        source_uri_pattern=source_uri_pattern,
                        is_partitioned=is_partitioned,
                        partition_columns=partition_columns,
                        created_time=table.created,
                        num_rows=table.num_rows,
                    )
                    external_tables.append(table_info)

            logger.info(f"Found {len(external_tables)} external tables in {self._dataset_id}")
            return external_tables

        except google_api_exceptions.NotFound as e:
            logger.error(f"Dataset not found: {e}")
            return []
        except google_api_exceptions.PermissionDenied as e:
            logger.error(f"Permission denied listing tables: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing tables: {e}", exc_info=True)
            return []

    @staticmethod
    def _extract_partition_columns(source_uri: str) -> List[str]:
        """Extract partition column names from GCS URI pattern.

        Example:
            gs://bucket/folder/report_date=*/file.csv.gz → ["report_date"]
        """
        # Find all patterns like "column_name=*"
        pattern = r"/(\w+)=\*"
        matches = re.findall(pattern, source_uri)
        return matches

    @retry_with_backoff(retries=3, exceptions=TRANSIENT_EXCEPTIONS)
    def create_external_table(
        self,
        table_name: str,
        storage_folder_name: str,
        use_hive_partitioning: bool = True,
        schema: Optional[List[bigquery.SchemaField]] = None,
        use_autodetect_fallback: bool = True,
    ) -> bool:
        """Create external table referencing GCS CSV files.

        Creates a BigQuery external table with:
        - CSV format with GZIP compression
        - Explicit schema with lowercase column names (or auto-detected schema)
        - Hive partitioning on report_date column (if enabled)

        Args:
            table_name: BigQuery table name (e.g., "claim_raw_v1_1")
            storage_folder_name: GCS folder path (e.g., "caravan-versioned/claim_raw_v1-1")
            use_hive_partitioning: Enable Hive partitioning (default: True)
            schema: Optional explicit schema. If None, will attempt to infer from CSV.
            use_autodetect_fallback: If schema inference fails, fall back to autodetect

        Returns:
            True if creation succeeded, False otherwise

        Example:
            >>> manager.create_external_table(
            ...     "claim_raw_v1_1",
            ...     "caravan-versioned/claim_raw_v1-1"
            ... )
            True
        """
        if self._has_error:
            return False

        try:
            # Construct table reference
            table_ref = f"{self.project_id}.{self._dataset_id}.{table_name}"

            # Build source URIs
            if use_hive_partitioning:
                source_uri_prefix = f"gs://{self.bucket_name}/{storage_folder_name}"
                # BigQuery limitation: Only single wildcard supported
                # Files must be filtered at upload time, not query time
                source_uris = [f"{source_uri_prefix}/*"]
            else:
                source_uris = [f"gs://{self.bucket_name}/{storage_folder_name}/*.csv.gz"]

            # Create external configuration for CSV
            external_config = bigquery.ExternalConfig("CSV")
            external_config.source_uris = source_uris
            external_config.compression = "GZIP"

            # Use explicit schema if provided, otherwise try to infer
            has_title_row = False
            if schema is None:
                from datawagon.bucket.schema_inference import SchemaInferenceManager

                schema_manager = SchemaInferenceManager(self.storage_client, self.bucket_name)
                inference_result = schema_manager.infer_schema(storage_folder_name)

                if inference_result is not None:
                    schema, has_title_row = inference_result
                else:
                    schema = None
            else:
                # When schema is provided explicitly, assume no title row
                # (in the future, this could be made configurable via a parameter)
                has_title_row = False

            # Set schema or fall back to autodetect
            if schema:
                external_config.schema = schema
                external_config.autodetect = False
                logger.info(f"Using explicit schema with {len(schema)} columns")
            elif use_autodetect_fallback:
                external_config.autodetect = True
                logger.warning(
                    f"Schema inference failed for {storage_folder_name}, "
                    "falling back to autodetect (column names may not be lowercase)"
                )
            else:
                logger.error("Schema inference failed and autodetect disabled")
                return False

            # Configure CSV-specific options
            csv_options = bigquery.CSVOptions()
            # Skip title row (if present) + header row
            skip_rows = 2 if has_title_row else 1
            csv_options.skip_leading_rows = skip_rows
            logger.info(f"CSV skip_leading_rows set to {skip_rows} (has_title_row={has_title_row})")
            external_config.csv_options = csv_options

            # Configure Hive partitioning if enabled
            if use_hive_partitioning:
                hive_partitioning = bigquery.HivePartitioningOptions()
                hive_partitioning.mode = "AUTO"
                hive_partitioning.source_uri_prefix = source_uri_prefix
                external_config.hive_partitioning = hive_partitioning

            # Create table
            table = bigquery.Table(table_ref)
            table.external_data_configuration = external_config

            created_table = self.bq_client.create_table(table)
            logger.info(f"Created external table: {created_table.full_table_id}")
            return True

        except google_api_exceptions.Conflict:
            logger.error(f"Table already exists: {table_name}")
            return False
        except google_api_exceptions.PermissionDenied as e:
            logger.error(f"Permission denied creating table: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating table: {e}", exc_info=True)
            return False

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists in dataset.

        Args:
            table_name: Name of table to check

        Returns:
            True if table exists, False otherwise
        """
        try:
            table_ref = f"{self.project_id}.{self._dataset_id}.{table_name}"
            self.bq_client.get_table(table_ref)
            return True
        except google_api_exceptions.NotFound:
            return False
        except Exception as e:
            logger.error(f"Error checking table existence: {e}", exc_info=True)
            return False

    @retry_with_backoff(retries=3, exceptions=TRANSIENT_EXCEPTIONS)
    def delete_table(self, table_name: str) -> bool:
        """Delete a BigQuery external table.

        Args:
            table_name: Name of table to delete

        Returns:
            True if deletion succeeded, False otherwise

        Note:
            Only deletes table metadata (external tables don't contain data in BigQuery).
            The underlying CSV files in GCS remain untouched.
        """
        if self._has_error:
            return False

        try:
            table_ref = f"{self.project_id}.{self._dataset_id}.{table_name}"
            self.bq_client.delete_table(table_ref)
            logger.info(f"Deleted external table: {table_ref}")
            return True

        except google_api_exceptions.NotFound:
            logger.error(f"Table not found: {table_name}")
            return False
        except google_api_exceptions.PermissionDenied as e:
            logger.error(f"Permission denied deleting table: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting table: {e}", exc_info=True)
            return False

    @property
    def has_error(self) -> bool:
        """Check if manager has encountered errors.

        Returns:
            True if manager is in error state, False otherwise

        Example:
            >>> if manager.has_error:
            ...     print("Cannot proceed - manager has errors")

        Note:
            This property is read-only. Error state is set internally during initialization
            and error handling. Cannot be modified externally to prevent masking errors.
        """
        return self._has_error

    @property
    def dataset_id(self) -> str:
        """Get the BigQuery dataset name.

        Returns:
            Name of the BigQuery dataset

        Example:
            >>> manager.dataset_id
            'youtube_analytics'
        """
        return self._dataset_id
