"""Tests for create_bigquery_tables command."""

from unittest.mock import Mock

from datawagon.commands.create_bigquery_tables import _scan_gcs_storage_folders


def test_scan_folders_with_prefix() -> None:
    """Test that storage prefix filters folders correctly."""
    # Mock GcsManager to return blobs from multiple folders
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = [
        "caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/file.csv.gz",
        "caravan-versioned/asset_raw_v1-1/report_date=2023-07-31/file.csv.gz",
    ]

    # Scan with prefix - should only find versioned folders
    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="caravan-versioned")

    # Should find 2 folders under caravan-versioned
    assert len(folders) == 2
    folder_names = {f.storage_folder_name for f in folders}
    assert "caravan-versioned/claim_raw_v1-1" in folder_names
    assert "caravan-versioned/asset_raw_v1-1" in folder_names

    # Verify prefix was used in the call
    mock_gcs.list_all_blobs_with_prefix.assert_called_once_with(prefix="caravan-versioned")


def test_scan_folders_without_prefix() -> None:
    """Test scanning all folders when no prefix is specified."""
    # Mock GcsManager to return blobs from multiple top-level folders
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = [
        "caravan/claim_raw/file1.csv.gz",
        "caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/file2.csv.gz",
    ]

    # Scan without prefix (empty string) - should find all folders
    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="")

    # Should find 2 folders (one in caravan, one in caravan-versioned)
    assert len(folders) == 2
    folder_names = {f.storage_folder_name for f in folders}
    assert "caravan/claim_raw" in folder_names
    assert "caravan-versioned/claim_raw_v1-1" in folder_names

    # Verify empty prefix was used in the call
    mock_gcs.list_all_blobs_with_prefix.assert_called_once_with(prefix="")


def test_scan_folders_with_nonexistent_prefix() -> None:
    """Test that non-existent prefix returns empty list."""
    # Mock GcsManager to return empty list (prefix doesn't match anything)
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = []

    # Scan with non-existent prefix
    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="nonexistent-prefix")

    # Should return empty list
    assert len(folders) == 0

    # Verify prefix was used in the call
    mock_gcs.list_all_blobs_with_prefix.assert_called_once_with(prefix="nonexistent-prefix")


def test_scan_folders_extracts_version() -> None:
    """Test that folder scanning correctly extracts version information."""
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = [
        "caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/file.csv.gz",
    ]

    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="caravan-versioned")

    assert len(folders) == 1
    folder = folders[0]
    assert folder.table_name == "claim_raw"
    assert folder.file_version == "v1-1"
    assert folder.proposed_bq_table_name == "claim_raw_v1_1"


def test_scan_folders_detects_partitioning() -> None:
    """Test that folder scanning detects Hive partitioning."""
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = [
        "caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/file.csv.gz",
    ]

    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="caravan-versioned")

    assert len(folders) == 1
    assert folders[0].has_partitioning is True


def test_scan_folders_without_partitioning() -> None:
    """Test that folder scanning correctly identifies non-partitioned folders."""
    mock_gcs = Mock()
    mock_gcs.list_all_blobs_with_prefix.return_value = [
        "caravan-versioned/simple_table/file.csv.gz",
    ]

    folders = _scan_gcs_storage_folders(mock_gcs, "test-bucket", storage_prefix="caravan-versioned")

    assert len(folders) == 1
    assert folders[0].has_partitioning is False
