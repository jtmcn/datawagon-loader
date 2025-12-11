"""Pytest fixtures and configuration."""

import gzip
import tempfile
import zipfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock

import pytest
from google.cloud import storage

from datawagon.objects.source_config import SourceConfig, SourceFromLocalFS


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_csv_content() -> str:
    """Sample CSV content for testing."""
    return "header1,header2,header3\nvalue1,value2,value3\n"


@pytest.fixture
def mock_source_config() -> SourceConfig:
    """Mock source configuration for testing."""
    return SourceConfig(
        file={
            "youtube_data": SourceFromLocalFS(
                is_enabled=True,
                select_file_name_base="YouTube_*_M_*",
                exclude_file_name_base=".~lock*",
                regex_pattern=r"YouTube_(.+)_M_(\d{8}|\d{6})",
                regex_group_names=["content_owner", "file_date_key"],
                storage_folder_name="youtube_analytics",
                table_name="youtube_raw",
                table_append_or_replace="append",
            )
        }
    )


@pytest.fixture
def mock_env_vars(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up mock environment variables."""
    monkeypatch.setenv("DW_CSV_SOURCE_DIR", str(temp_dir))
    monkeypatch.setenv("DW_GCS_PROJECT_ID", "test-project")
    monkeypatch.setenv("DW_GCS_BUCKET", "test-bucket")


@pytest.fixture
def sample_csv_file(temp_dir: Path, sample_csv_content: str) -> Path:
    """Create a sample CSV file."""
    csv_file = temp_dir / "test.csv"
    csv_file.write_text(sample_csv_content)
    return csv_file


@pytest.fixture
def sample_gzipped_csv(temp_dir: Path, sample_csv_content: str) -> Path:
    """Create a gzipped CSV file."""
    gz_file = temp_dir / "test.csv.gz"
    with gzip.open(gz_file, "wt") as f:
        f.write(sample_csv_content)
    return gz_file


@pytest.fixture
def sample_zipped_csv(temp_dir: Path, sample_csv_content: str) -> Path:
    """Create a zipped CSV file."""
    zip_file = temp_dir / "test.csv.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("test.csv", sample_csv_content)
    return zip_file


@pytest.fixture
def youtube_file_in_temp_dir(temp_dir: Path, sample_csv_content: str) -> Path:
    """Create a properly named YouTube file in temp directory."""
    filename = "YouTube_BrandName_M_20230601_claim_raw_v1-1.csv.gz"
    file_path = temp_dir / filename
    with gzip.open(file_path, "wt") as f:
        f.write(sample_csv_content)
    return file_path


@pytest.fixture
def mock_gcs_client() -> Mock:
    """Mock Google Cloud Storage client."""
    client = Mock(spec=storage.Client)
    bucket = Mock(spec=storage.Bucket)
    blob = Mock(spec=storage.Blob)

    # Setup relationships
    client.bucket.return_value = bucket
    bucket.blob.return_value = blob
    bucket.list_blobs.return_value = []

    return client
