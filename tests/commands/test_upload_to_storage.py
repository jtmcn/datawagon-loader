"""Tests for upload_to_storage command."""

from pathlib import Path
from typing import List
from unittest.mock import Mock, patch

import click
import pytest

from datawagon.commands.upload_to_storage import upload_all_gzip_csv
from datawagon.objects.app_config import AppConfig
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import ManagedFilesToDatabase


@pytest.fixture
def mock_context() -> click.Context:
    """Create a real Click context for testing."""
    from datawagon.commands.upload_to_storage import upload_all_gzip_csv

    # Create a real Click context (not a Mock)
    ctx = click.Context(upload_all_gzip_csv)
    ctx.params = {}
    ctx.obj = {
        "CONFIG": AppConfig(
            csv_source_dir=Path("/test/source"),
            csv_source_config=Path("/test/config.toml"),
            gcs_project_id="test-project",
            gcs_bucket="test-bucket",
            bq_dataset="test_dataset",
        )
    }
    return ctx


@pytest.fixture
def sample_file_metadata() -> ManagedFileMetadata:
    """Create sample file metadata for testing."""
    return ManagedFileMetadata(
        content_owner="test_owner",
        file_date_key=None,
        report_date_key=20230630,
        report_date_str="2023-06-30",
        file_version="v1-1",
        base_name="claim_raw",
        file_name="YouTube_TestOwner_M_20230630_claim_raw_v1-1.csv.gz",
        file_path=Path("/test/source/YouTube_TestOwner_M_20230630_claim_raw_v1-1.csv.gz"),
        file_dir="/test/source",
        file_size_in_bytes=1024,
        file_size="1.00 KB",
        storage_folder_name="claim_raw_v1-1",
        table_name="claim_raw",
        table_append_or_replace="replace",
    )


def test_upload_success_with_partitioned_files(
    mock_context: click.Context, sample_file_metadata: ManagedFileMetadata
) -> None:
    """Test successful upload of partitioned files."""
    # Mock compare command to return files to upload
    mock_files_to_upload = [
        ManagedFilesToDatabase(
            files=[sample_file_metadata],
            file_selector_base_name="claim_raw",
            table_name="claim_raw",
            table_append_or_replace="replace",
        )
    ]

    with patch("datawagon.commands.upload_to_storage.GcsManager") as mock_gcs_class, patch(
        "datawagon.commands.upload_to_storage.confirm"
    ) as mock_confirm:
        mock_gcs = Mock()
        mock_gcs.has_error = False
        mock_gcs.upload_blob.return_value = True
        mock_gcs_class.return_value = mock_gcs
        mock_context.obj["GCS_MANAGER"] = mock_gcs

        # Mock invoke to return the test data
        with patch.object(mock_context, "invoke") as mock_invoke:
            mock_invoke.return_value = mock_files_to_upload

            # Use context manager and call callback
            with mock_context:  # type: ignore[attr-defined]
                upload_all_gzip_csv.callback()  # type: ignore[misc]

        # Verify confirm was called
        mock_confirm.assert_called_once()

        # Verify upload_blob was called with correct path
        mock_gcs.upload_blob.assert_called_once()
        call_args = mock_gcs.upload_blob.call_args
        assert "claim_raw_v1-1/report_date=2023-06-30/" in call_args[0][1]


def test_upload_success_without_partitioning(mock_context: click.Context) -> None:
    """Test successful upload of non-partitioned files."""
    # Create file metadata without report_date_str
    file_metadata = ManagedFileMetadata(
        content_owner="test_owner",
        file_date_key=None,
        report_date_key=None,
        report_date_str=None,  # No partitioning
        file_version="v1-1",
        base_name="claim_raw",
        file_name="YouTube_TestOwner_M_20230630_claim_raw_v1-1.csv.gz",
        file_path=Path("/test/source/YouTube_TestOwner_M_20230630_claim_raw_v1-1.csv.gz"),
        file_dir="/test/source",
        file_size_in_bytes=1024,
        file_size="1.00 KB",
        storage_folder_name="claim_raw_v1-1",
        table_name="claim_raw",
        table_append_or_replace="replace",
    )

    mock_files_to_upload = [
        ManagedFilesToDatabase(
            files=[file_metadata],
            file_selector_base_name="claim_raw",
            table_name="claim_raw",
            table_append_or_replace="replace",
        )
    ]

    with patch("datawagon.commands.upload_to_storage.GcsManager") as mock_gcs_class, patch(
        "datawagon.commands.upload_to_storage.confirm"
    ) as mock_confirm:
        mock_gcs = Mock()
        mock_gcs.has_error = False
        mock_gcs.upload_blob.return_value = True
        mock_gcs_class.return_value = mock_gcs
        mock_context.obj["GCS_MANAGER"] = mock_gcs

        # Mock invoke to return the test data
        with patch.object(mock_context, "invoke") as mock_invoke:
            mock_invoke.return_value = mock_files_to_upload

            # Use context manager and call callback
            with mock_context:  # type: ignore[attr-defined]
                upload_all_gzip_csv.callback()  # type: ignore[misc]

        # Verify confirm was called
        mock_confirm.assert_called_once()

        # Verify upload_blob was called with non-partitioned path
        mock_gcs.upload_blob.assert_called_once()
        call_args = mock_gcs.upload_blob.call_args
        assert "report_date=" not in call_args[0][1]
        assert "claim_raw_v1-1/" in call_args[0][1]


def test_upload_rejects_non_gzip_files_in_partitioned_folder(mock_context: click.Context) -> None:
    """Test that non-.csv.gz files are rejected for partitioned uploads."""
    # Create file metadata with .csv.zip extension (not allowed for partitioning)
    file_metadata = ManagedFileMetadata(
        content_owner="test_owner",
        file_date_key=None,
        report_date_key=20230630,
        report_date_str="2023-06-30",  # Has partitioning
        file_version="v1-1",
        base_name="claim_raw",
        file_name="YouTube_TestOwner_M_20230630_claim_raw_v1-1.csv.zip",  # Wrong extension
        file_path=Path("/test/source/YouTube_TestOwner_M_20230630_claim_raw_v1-1.csv.zip"),
        file_dir="/test/source",
        file_size_in_bytes=1024,
        file_size="1.00 KB",
        storage_folder_name="claim_raw_v1-1",
        table_name="claim_raw",
        table_append_or_replace="replace",
    )

    mock_files_to_upload = [
        ManagedFilesToDatabase(
            files=[file_metadata],
            file_selector_base_name="claim_raw",
            table_name="claim_raw",
            table_append_or_replace="replace",
        )
    ]

    with patch("datawagon.commands.upload_to_storage.GcsManager") as mock_gcs_class, patch(
        "datawagon.commands.upload_to_storage.confirm"
    ):
        mock_gcs = Mock()
        mock_gcs.has_error = False
        mock_gcs_class.return_value = mock_gcs
        mock_context.obj["GCS_MANAGER"] = mock_gcs

        # Mock invoke to return the test data
        with patch.object(mock_context, "invoke") as mock_invoke:
            mock_invoke.return_value = mock_files_to_upload

            # Use context manager and call callback
            with mock_context:  # type: ignore[attr-defined]
                upload_all_gzip_csv.callback()  # type: ignore[misc]

        # Verify upload_blob was NOT called (file was skipped)
        mock_gcs.upload_blob.assert_not_called()


def test_upload_no_new_files(mock_context: click.Context) -> None:
    """Test command behavior when no new files to upload."""
    # Mock compare command to return empty list
    mock_files_to_upload: List[ManagedFilesToDatabase] = []

    # Add a mock GCS manager to context to prevent real GCS connection
    mock_gcs = Mock()
    mock_gcs.has_error = False
    mock_context.obj["GCS_MANAGER"] = mock_gcs

    with patch("datawagon.commands.upload_to_storage.confirm") as mock_confirm:
        # Mock invoke to return the test data
        with patch.object(mock_context, "invoke") as mock_invoke:
            mock_invoke.return_value = mock_files_to_upload

            # Use context manager and call callback
            with mock_context:  # type: ignore[attr-defined]
                upload_all_gzip_csv.callback()  # type: ignore[misc]

        # Verify confirm was NOT called (no files to upload)
        mock_confirm.assert_not_called()


def test_upload_gcs_connection_error_lazy_init(mock_context: click.Context) -> None:
    """Test handling of GCS connection error during lazy initialization."""
    # Remove GCS_MANAGER from context to trigger lazy init
    mock_context.obj = {"CONFIG": mock_context.obj["CONFIG"]}

    # Mock compare command to return files
    file_metadata = ManagedFileMetadata(
        content_owner="test_owner",
        file_date_key=None,
        report_date_key=20230630,
        report_date_str="2023-06-30",
        file_version="v1-1",
        base_name="claim_raw",
        file_name="YouTube_TestOwner_M_20230630_claim_raw_v1-1.csv.gz",
        file_path=Path("/test/source/YouTube_TestOwner_M_20230630_claim_raw_v1-1.csv.gz"),
        file_dir="/test/source",
        file_size_in_bytes=1024,
        file_size="1.00 KB",
        storage_folder_name="claim_raw_v1-1",
        table_name="claim_raw",
        table_append_or_replace="replace",
    )
    mock_files_to_upload = [
        ManagedFilesToDatabase(
            files=[file_metadata],
            file_selector_base_name="claim_raw",
            table_name="claim_raw",
            table_append_or_replace="replace",
        )
    ]

    with patch("datawagon.commands.upload_to_storage.GcsManager") as mock_gcs_class:
        mock_gcs = Mock()
        mock_gcs.has_error = True
        mock_gcs_class.return_value = mock_gcs

        # Mock invoke to return the test data and abort to raise exception (like Click does)
        with patch.object(mock_context, "invoke") as mock_invoke, patch.object(
            mock_context, "abort", side_effect=click.exceptions.Abort()
        ) as mock_abort:
            mock_invoke.return_value = mock_files_to_upload

            # Use context manager and call callback, expecting Abort exception
            with pytest.raises(click.exceptions.Abort):  # type: ignore[attr-defined]
                with mock_context:  # type: ignore[attr-defined]
                    upload_all_gzip_csv.callback()  # type: ignore[misc]

            # Verify abort was called due to GCS connection error
            mock_abort.assert_called_once()


def test_upload_partial_failure(mock_context: click.Context, sample_file_metadata: ManagedFileMetadata) -> None:
    """Test upload with some files failing."""
    # Create two files
    file1 = sample_file_metadata
    file2 = ManagedFileMetadata(
        content_owner="test_owner",
        file_date_key=None,
        report_date_key=20230630,
        report_date_str="2023-06-30",
        file_version="v1-1",
        base_name="claim_raw",
        file_name="file2.csv.gz",
        file_path=Path("/test/source/file2.csv.gz"),
        file_dir="/test/source",
        file_size_in_bytes=1024,
        file_size="1.00 KB",
        storage_folder_name="claim_raw_v1-1",
        table_name="claim_raw",
        table_append_or_replace="replace",
    )

    mock_files_to_upload = [
        ManagedFilesToDatabase(
            files=[file1, file2],
            file_selector_base_name="claim_raw",
            table_name="claim_raw",
            table_append_or_replace="replace",
        )
    ]

    with patch("datawagon.commands.upload_to_storage.GcsManager") as mock_gcs_class, patch(
        "datawagon.commands.upload_to_storage.confirm"
    ) as mock_confirm:
        mock_gcs = Mock()
        mock_gcs.has_error = False
        # First upload succeeds, second fails
        mock_gcs.upload_blob.side_effect = [True, False]
        mock_gcs_class.return_value = mock_gcs
        mock_context.obj["GCS_MANAGER"] = mock_gcs

        # Mock invoke to return the test data
        with patch.object(mock_context, "invoke") as mock_invoke:
            mock_invoke.return_value = mock_files_to_upload

            # Use context manager and call callback
            with mock_context:  # type: ignore[attr-defined]
                upload_all_gzip_csv.callback()  # type: ignore[misc]

        # Verify confirm was called
        mock_confirm.assert_called_once()

        # Verify upload_blob was called twice
        assert mock_gcs.upload_blob.call_count == 2
