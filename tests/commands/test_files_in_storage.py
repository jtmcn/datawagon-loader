"""Tests for files_in_storage command."""

from unittest.mock import Mock, patch

import click
import pandas as pd
import pytest

from datawagon.commands.files_in_storage import files_in_storage
from datawagon.objects.app_config import AppConfig
from datawagon.objects.current_table_data import CurrentDestinationData
from datawagon.objects.source_config import SourceConfig


@pytest.fixture
def mock_context() -> click.Context:
    """Create a real Click context for testing."""
    from pathlib import Path

    from datawagon.commands.files_in_storage import files_in_storage

    # Create a real Click context (not a Mock)
    ctx = click.Context(files_in_storage)
    ctx.params = {}
    ctx.obj = {
        "CONFIG": AppConfig(
            csv_source_dir=Path("/test/source"),
            csv_source_config=Path("/test/config.toml"),
            gcs_project_id="test-project",
            gcs_bucket="test-bucket",
            bq_dataset="test_dataset",
        ),
        "FILE_CONFIG": Mock(spec=SourceConfig),
    }
    return ctx


def test_files_in_storage_success(mock_context: click.Context) -> None:
    """Test successful retrieval of files from storage."""
    # Mock DataFrame with sample blob data
    mock_df = pd.DataFrame(
        {
            "base_name": ["claim_raw", "claim_raw", "asset_raw"],
            "_file_name": ["file1.csv.gz", "file2.csv.gz", "file3.csv.gz"],
        }
    )

    with patch("datawagon.commands.files_in_storage.GcsManager") as mock_gcs_class:
        mock_gcs = Mock()
        mock_gcs.has_error = False
        mock_gcs.files_in_blobs_df.return_value = mock_df
        mock_gcs_class.return_value = mock_gcs

        # Use context manager and call callback
        with mock_context:  # type: ignore[attr-defined]
            result = files_in_storage.callback()  # type: ignore[misc]

        # Verify GcsManager was created with correct parameters
        mock_gcs_class.assert_called_once_with("test-project", "test-bucket")

        # Verify files_in_blobs_df was called
        mock_gcs.files_in_blobs_df.assert_called_once()

        # Verify result contains correct table data
        assert len(result) == 2
        assert isinstance(result[0], CurrentDestinationData)
        assert isinstance(result[1], CurrentDestinationData)

        # Check claim_raw table
        claim_data = next(d for d in result if d.base_name == "claim_raw")
        assert claim_data.file_count == 2
        assert "file1.csv.gz" in claim_data.source_files
        assert "file2.csv.gz" in claim_data.source_files

        # Check asset_raw table
        asset_data = next(d for d in result if d.base_name == "asset_raw")
        assert asset_data.file_count == 1
        assert "file3.csv.gz" in asset_data.source_files

        # Verify GCS manager was stored in context
        assert mock_context.obj["GCS_MANAGER"] == mock_gcs


def test_files_in_storage_gcs_connection_error(mock_context: click.Context) -> None:
    """Test handling of GCS connection failure."""
    with patch("datawagon.commands.files_in_storage.GcsManager") as mock_gcs_class:
        mock_gcs = Mock()
        mock_gcs.has_error = True
        mock_gcs_class.return_value = mock_gcs

        # Mock the abort method to raise an exception (like Click does)
        with patch.object(mock_context, "abort", side_effect=click.exceptions.Abort()) as mock_abort:
            # Use context manager and call callback, expecting Abort exception
            with pytest.raises(click.exceptions.Abort):  # type: ignore[attr-defined]
                with mock_context:  # type: ignore[attr-defined]
                    files_in_storage.callback()  # type: ignore[misc]

            # Verify abort was called
            mock_abort.assert_called_once()


def test_files_in_storage_empty_bucket(mock_context: click.Context) -> None:
    """Test command with empty storage bucket."""
    # Mock empty DataFrame
    mock_df = pd.DataFrame({"base_name": [], "_file_name": []})

    with patch("datawagon.commands.files_in_storage.GcsManager") as mock_gcs_class:
        mock_gcs = Mock()
        mock_gcs.has_error = False
        mock_gcs.files_in_blobs_df.return_value = mock_df
        mock_gcs_class.return_value = mock_gcs

        # Use context manager and call callback
        with mock_context:  # type: ignore[attr-defined]
            result = files_in_storage.callback()  # type: ignore[misc]

        # Verify empty result
        assert len(result) == 0


def test_files_in_storage_single_base_name(mock_context: click.Context) -> None:
    """Test command with single base name containing multiple files."""
    # Mock DataFrame with single base name
    mock_df = pd.DataFrame(
        {
            "base_name": ["claim_raw", "claim_raw", "claim_raw"],
            "_file_name": ["file1.csv.gz", "file2.csv.gz", "file3.csv.gz"],
        }
    )

    with patch("datawagon.commands.files_in_storage.GcsManager") as mock_gcs_class:
        mock_gcs = Mock()
        mock_gcs.has_error = False
        mock_gcs.files_in_blobs_df.return_value = mock_df
        mock_gcs_class.return_value = mock_gcs

        # Use context manager and call callback
        with mock_context:  # type: ignore[attr-defined]
            result = files_in_storage.callback()  # type: ignore[misc]

        # Verify single table with 3 files
        assert len(result) == 1
        assert result[0].base_name == "claim_raw"
        assert result[0].file_count == 3
        assert len(result[0].source_files) == 3
