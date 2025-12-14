"""Tests for BigQueryManager."""

from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from datawagon.bucket.bigquery_manager import BigQueryManager


class BigQueryManagerTestCase(TestCase):
    """Test cases for BigQueryManager."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Mock the BigQuery and Storage clients
        with patch("datawagon.bucket.bigquery_manager.bigquery.Client"), patch(
            "datawagon.bucket.bigquery_manager.storage.Client"
        ):
            self.manager = BigQueryManager(
                project_id="test-project", bucket_name="test-bucket", dataset_id="test_dataset"
            )
            self.manager.bq_client = Mock()
            self.manager.storage_client = Mock()

    def test_hive_partitioning_source_uri_filters_extension(self) -> None:
        """Verify Hive partitioning source URI only matches .csv.gz files."""
        # Mock schema to avoid schema inference
        mock_schema = [MagicMock()]

        # Mock the create_table method
        with patch.object(self.manager.bq_client, "create_table") as mock_create:
            # Call the method with Hive partitioning enabled
            result = self.manager.create_external_table(
                table_name="test_table",
                storage_folder_name="test_folder",
                schema=mock_schema,
                use_hive_partitioning=True,
            )

            # Verify the method succeeded
            assert result is True, "create_external_table should return True"
            assert mock_create.called, "create_table should have been called"

            # Get the Table object that was passed to create_table
            call_args = mock_create.call_args
            table = call_args[0][0]

            # Verify source URI uses single wildcard only (BigQuery limitation)
            source_uris = table.external_data_configuration.source_uris
            assert len(source_uris) == 1, "Should have exactly one source URI"
            assert (
                source_uris[0] == "gs://test-bucket/test_folder/*"
            ), f"Source URI should use single wildcard for Hive partitioning, got: {source_uris[0]}"
            assert source_uris[0].count("*") == 1, "Should have exactly one wildcard (BigQuery limitation)"

            # Verify compression is set to GZIP
            assert table.external_data_configuration.compression == "GZIP", "Compression should be GZIP"

            # Verify Hive partitioning is enabled
            assert (
                table.external_data_configuration.hive_partitioning is not None
            ), "Hive partitioning should be enabled"

    def test_non_hive_partitioning_source_uri(self) -> None:
        """Verify non-Hive partitioning source URI pattern."""
        # Mock schema to avoid schema inference
        mock_schema = [MagicMock()]

        # Mock the create_table method
        with patch.object(self.manager.bq_client, "create_table") as mock_create:
            # Call the method with Hive partitioning disabled
            result = self.manager.create_external_table(
                table_name="test_table",
                storage_folder_name="test_folder",
                schema=mock_schema,
                use_hive_partitioning=False,
            )

            # Verify the method succeeded
            assert result is True, "create_external_table should return True"
            assert mock_create.called, "create_table should have been called"

            # Get the Table object that was passed to create_table
            call_args = mock_create.call_args
            table = call_args[0][0]

            # Verify source URI pattern for non-Hive partitioning
            source_uris = table.external_data_configuration.source_uris
            assert len(source_uris) == 1, "Should have exactly one source URI"
            assert (
                source_uris[0] == "gs://test-bucket/test_folder/*.csv.gz"
            ), f"Source URI should match .csv.gz files directly, got: {source_uris[0]}"

            # Verify Hive partitioning is NOT enabled
            assert table.external_data_configuration.hive_partitioning is None, "Hive partitioning should be disabled"
