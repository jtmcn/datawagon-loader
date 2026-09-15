"""Tests for GcsManager (all GCS clients mocked)."""

from io import BytesIO
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from google.api_core import exceptions as gexc

from datawagon.bucket.gcs_manager import GcsManager
from datawagon.objects.source_config import SourceConfig, SourceFromLocalFS

BUCKET = "test-bucket"


@pytest.fixture(autouse=True)
def mock_logger() -> Iterator[Mock]:
    # The datawagon logger may have propagate=False (setup_logging), so caplog is unreliable
    with patch("datawagon.bucket.gcs_manager.logger") as log:
        yield log


@pytest.fixture(autouse=True)
def no_sleep() -> Iterator[Mock]:
    with patch("datawagon.bucket.retry_utils.time.sleep") as sleep:
        yield sleep


@pytest.fixture
def client_cls(mock_gcs_client: Mock) -> Iterator[Mock]:
    mock_gcs_client.list_buckets.return_value = []
    with patch("datawagon.bucket.gcs_manager.storage.Client", return_value=mock_gcs_client) as cls:
        yield cls


@pytest.fixture
def manager(client_cls: Mock) -> GcsManager:
    return GcsManager("test-project", BUCKET)


@pytest.fixture
def client(manager: GcsManager) -> Any:
    return manager.storage_client


def _named(*names: str) -> list[Mock]:
    blobs = []
    for n in names:
        b = Mock()
        b.name = n
        blobs.append(b)
    return blobs


def _error_calls(log: Mock) -> str:
    return " ".join(str(c.args[0]) for c in log.error.call_args_list)


# --- __init__ ---


def test_init_success_logs_buckets(mock_gcs_client: Mock, client_cls: Mock, mock_logger: Mock) -> None:
    mock_gcs_client.list_buckets.return_value = _named("b1", "b2")
    m = GcsManager("proj", BUCKET)
    client_cls.assert_called_once_with(project="proj")
    assert m.has_error is False
    assert m.bucket_name == BUCKET
    mock_logger.info.assert_any_call("Found GCS bucket: b1")
    mock_logger.info.assert_any_call("Found GCS bucket: b2")


@pytest.mark.parametrize(
    "exc, fragment",
    [
        (gexc.Unauthenticated("no creds"), "gcloud auth application-default login"),
        (gexc.PermissionDenied("nope"), "permission denied"),
        (RuntimeError("boom"), "Error connecting to GCS"),
    ],
)
def test_init_errors_set_has_error(
    mock_gcs_client: Mock, client_cls: Mock, mock_logger: Mock, exc: Exception, fragment: str
) -> None:
    mock_gcs_client.list_buckets.side_effect = exc
    m = GcsManager("proj", BUCKET)
    assert m.has_error is True
    assert fragment in _error_calls(mock_logger)


# --- simple accessors ---


def test_list_buckets_returns_names(manager: GcsManager, client: Mock) -> None:
    client.list_buckets.return_value = _named("a", "b")
    assert manager.list_buckets() == ["a", "b"]


def test_has_error_setter(manager: GcsManager) -> None:
    manager.has_error = True
    assert manager.has_error is True
    manager.has_error = False
    assert manager.has_error is False


def test_delete_blob(manager: GcsManager, client: Mock) -> None:
    manager.delete_blob("x/y.csv")
    client.bucket.assert_called_with(BUCKET)
    client.bucket.return_value.blob.assert_called_with("x/y.csv")
    client.bucket.return_value.blob.return_value.delete.assert_called_once_with()


def test_get_blob_and_metadata(manager: GcsManager, client: Mock) -> None:
    blob = client.bucket.return_value.blob.return_value
    blob.metadata = {"k": "v"}
    assert manager.get_blob("a.csv") is blob
    assert manager.get_blob_metadata("a.csv") == {"k": "v"}
    client.bucket.return_value.blob.assert_called_with("a.csv")


def test_download_blob(manager: GcsManager, client: Mock) -> None:
    manager.download_blob("a.csv", "/tmp/out.csv")
    client.bucket.return_value.blob.return_value.download_to_filename.assert_called_once_with("/tmp/out.csv")


def test_read_blob_to_memory_returns_rewound_buffer(manager: GcsManager, client: Mock) -> None:
    blob = client.bucket.return_value.blob.return_value
    blob.download_to_file.side_effect = lambda buf: buf.write(b"hello")
    result = manager.read_blob_to_memory("a.csv")
    assert isinstance(result, BytesIO)
    assert result.tell() == 0
    assert result.read() == b"hello"


# --- list_blobs ---


def test_list_blobs_nested_folder_builds_prefix_and_glob(manager: GcsManager, client: Mock) -> None:
    client.list_blobs.return_value = _named("caravan/claim_raw/report_date=2023-06-01/f.csv.gz")
    result = manager.list_blobs("caravan/claim_raw", "YouTube_X", ".csv.gz")
    assert result == ["caravan/claim_raw/report_date=2023-06-01/f.csv.gz"]
    client.list_blobs.assert_called_once_with(BUCKET, prefix="caravan/", match_glob="**claim_raw*/**YouTube_X**.csv.gz")


def test_list_blobs_flat_folder_uses_empty_prefix(manager: GcsManager, client: Mock) -> None:
    client.list_blobs.return_value = []
    assert manager.list_blobs("claim_raw", "base", ".csv") == []
    client.list_blobs.assert_called_once_with(BUCKET, prefix="", match_glob="**claim_raw*/**base**.csv")


def test_list_blobs_short_circuits_when_in_error(manager: GcsManager, client: Mock) -> None:
    manager.has_error = True
    assert manager.list_blobs("f", "b", ".csv") == []
    client.list_blobs.assert_not_called()


def test_list_blobs_not_found_returns_empty(manager: GcsManager, client: Mock, mock_logger: Mock) -> None:
    client.list_blobs.side_effect = gexc.NotFound("gone")
    assert manager.list_blobs("f", "b", ".csv") == []
    mock_logger.warning.assert_called_once_with(f"Bucket not found: {BUCKET}")
    assert manager.has_error is False


@pytest.mark.parametrize("exc", [gexc.Unauthenticated("x"), gexc.PermissionDenied("x")])
def test_list_blobs_auth_errors_reraise_and_flag(manager: GcsManager, client: Mock, exc: Exception) -> None:
    client.list_blobs.side_effect = exc
    with pytest.raises(type(exc)):
        manager.list_blobs("f", "b", ".csv")
    assert manager.has_error is True
    client.list_blobs.assert_called_once()  # not a transient error, so no retry


def test_list_blobs_generic_error_returns_empty(manager: GcsManager, client: Mock, mock_logger: Mock) -> None:
    client.list_blobs.side_effect = RuntimeError("weird")
    assert manager.list_blobs("f", "b", ".csv") == []
    assert "Unable to list files in bucket" in _error_calls(mock_logger)


def _failing_pages(exc: Exception) -> Iterator[Mock]:
    # list_blobs() is lazy: real HTTP errors surface while iterating, not on the call
    raise exc
    yield Mock()  # pragma: no cover


def test_list_blobs_retries_transient_error(manager: GcsManager, client: Mock, no_sleep: Mock) -> None:
    client.list_blobs.side_effect = [gexc.ServiceUnavailable("503"), _named("a/b.csv")]
    assert manager.list_blobs("f", "b", ".csv") == ["a/b.csv"]
    assert client.list_blobs.call_count == 2
    no_sleep.assert_called_once()


def test_list_blobs_retries_error_raised_during_iteration(manager: GcsManager, client: Mock) -> None:
    client.list_blobs.side_effect = [_failing_pages(gexc.TooManyRequests("429")), _named("a/b.csv")]
    assert manager.list_blobs("f", "b", ".csv") == ["a/b.csv"]


def test_list_blobs_transient_error_exhausted_returns_empty(
    manager: GcsManager, client: Mock, no_sleep: Mock, mock_logger: Mock
) -> None:
    client.list_blobs.side_effect = gexc.ServiceUnavailable("503")
    assert manager.list_blobs("f", "b", ".csv") == []
    assert client.list_blobs.call_count == 4  # first attempt + 3 retries
    assert no_sleep.call_count == 3
    assert "Unable to list files in bucket" in _error_calls(mock_logger)


# --- files_in_blobs_df ---


def _source(enabled: bool, base: str, folder: str | None) -> SourceFromLocalFS:
    return SourceFromLocalFS(
        is_enabled=enabled,
        select_file_name_base=base,
        exclude_file_name_base=".~lock*",
        regex_pattern=r"(.+)",
        regex_group_names=["content_owner"],
        storage_folder_name=folder,
        table_name="t",
    )


def test_files_in_blobs_df_combines_enabled_sources(manager: GcsManager) -> None:
    config = SourceConfig(
        file={
            "a": _source(True, "A_*", "caravan/a"),
            "b": _source(True, "B_*", None),
            "off": _source(False, "C_*", "c"),
        }
    )
    listings = {
        "caravan/a": ["caravan/a/report_date=1/a1.csv.gz", "caravan/a/report_date=2/a2.csv.gz"],
        "B_*": ["b1.csv.gz"],
    }
    with patch.object(GcsManager, "list_blobs", side_effect=lambda folder, *_: listings[folder]) as lb:
        df = manager.files_in_blobs_df(config)

    # storage_folder_name falls back to select_file_name_base; disabled source skipped
    assert [c.args for c in lb.call_args_list] == [
        ("caravan/a", "A_*", ".csv.gz"),
        ("B_*", "B_*", ".csv.gz"),
    ]
    expected = pd.DataFrame({"_file_name": ["a1.csv.gz", "a2.csv.gz", "b1.csv.gz"], "base_name": ["A_*", "A_*", "B_*"]})
    pd.testing.assert_frame_equal(df, expected, check_dtype=False)
    assert list(df.index) == [0, 1, 2]


def test_files_in_blobs_df_no_sources_is_empty(manager: GcsManager) -> None:
    df = manager.files_in_blobs_df(SourceConfig(file={}))
    assert df.empty
    assert list(df.columns) == ["_file_name", "base_name"]


# --- upload_blob ---


@pytest.fixture
def local_file(temp_dir: Path) -> Path:
    f = temp_dir / "f.csv.gz"
    f.write_bytes(b"x" * 100)
    return f


@pytest.mark.parametrize("overwrite, generation", [(False, 0), (True, None)])
def test_upload_blob_success(
    manager: GcsManager, client: Mock, local_file: Path, overwrite: bool, generation: int | None
) -> None:
    blob = client.bucket.return_value.blob.return_value
    blob.size = 100
    assert manager.upload_blob(str(local_file), "dir/report_date=2023-06-01/f.csv.gz", overwrite=overwrite) is True
    client.bucket.return_value.blob.assert_called_once_with("dir/report_date=2023-06-01/f.csv.gz")
    blob.upload_from_filename.assert_called_once_with(str(local_file), if_generation_match=generation)
    blob.reload.assert_called_once_with()


def test_upload_blob_size_mismatch_returns_false(
    manager: GcsManager, client: Mock, local_file: Path, mock_logger: Mock
) -> None:
    client.bucket.return_value.blob.return_value.size = 99
    assert manager.upload_blob(str(local_file), "dir/f.csv.gz") is False
    assert "Upload verification failed: local=100B, remote=99B" in _error_calls(mock_logger)


@pytest.mark.parametrize("bad", ["../etc/passwd", "/abs/path", "a%2F..%2Fb", "a\x00b"])
def test_upload_blob_invalid_name_raises_value_error(
    manager: GcsManager, client: Mock, local_file: Path, bad: str
) -> None:
    with pytest.raises(ValueError, match="Invalid destination blob name"):
        manager.upload_blob(str(local_file), bad)
    client.bucket.assert_not_called()


@pytest.mark.parametrize(
    "exc, method, fragment",
    [
        (gexc.PreconditionFailed("exists"), "warning", "Blob already exists"),
        (gexc.PermissionDenied("no"), "error", "Permission denied"),
        (gexc.NotFound("no bucket"), "error", "Bucket not found"),
        (RuntimeError("boom"), "error", "Unable to upload file"),
    ],
)
def test_upload_blob_errors_return_false(
    manager: GcsManager,
    client: Mock,
    local_file: Path,
    mock_logger: Mock,
    exc: Exception,
    method: str,
    fragment: str,
) -> None:
    client.bucket.return_value.blob.return_value.upload_from_filename.side_effect = exc
    assert manager.upload_blob(str(local_file), "dir/f.csv.gz") is False
    assert fragment in str(getattr(mock_logger, method).call_args.args[0])


def test_upload_blob_retries_transient_error(
    manager: GcsManager, client: Mock, local_file: Path, no_sleep: Mock
) -> None:
    blob = client.bucket.return_value.blob.return_value
    blob.size = 100
    blob.upload_from_filename.side_effect = [gexc.TooManyRequests("429"), None]
    assert manager.upload_blob(str(local_file), "dir/f.csv.gz") is True
    assert blob.upload_from_filename.call_count == 2
    no_sleep.assert_called_once()


def test_upload_blob_transient_error_exhausted_returns_false(
    manager: GcsManager, client: Mock, local_file: Path, mock_logger: Mock
) -> None:
    upload = client.bucket.return_value.blob.return_value.upload_from_filename
    upload.side_effect = gexc.InternalServerError("500")
    assert manager.upload_blob(str(local_file), "dir/f.csv.gz") is False
    assert upload.call_count == 4
    assert "Unable to upload file" in _error_calls(mock_logger)


def test_upload_blob_missing_local_file_raises(manager: GcsManager, temp_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        manager.upload_blob(str(temp_dir / "missing.csv.gz"), "dir/f.csv.gz")


# --- copy_blob_within_bucket ---


def _setup_copy(client: Mock, src_size: int, dst_size: int) -> tuple[Mock, Mock]:
    bucket = client.bucket.return_value
    src = bucket.blob.return_value
    src.size = src_size
    dst = Mock()
    dst.size = dst_size
    bucket.copy_blob.return_value = dst
    return src, dst


def test_copy_blob_success(manager: GcsManager, client: Mock) -> None:
    src, dst = _setup_copy(client, 50, 50)
    assert manager.copy_blob_within_bucket("a/src.csv", "b/dst.csv") is True
    bucket = client.bucket.return_value
    bucket.blob.assert_called_once_with("a/src.csv")
    bucket.copy_blob.assert_called_once_with(src, bucket, "b/dst.csv")
    src.reload.assert_called_once_with()
    dst.reload.assert_called_once_with()


def test_copy_blob_size_mismatch(manager: GcsManager, client: Mock, mock_logger: Mock) -> None:
    _setup_copy(client, 50, 49)
    assert manager.copy_blob_within_bucket("a/src.csv", "b/dst.csv") is False
    assert "Size mismatch" in _error_calls(mock_logger)


def test_copy_blob_invalid_destination(manager: GcsManager, client: Mock) -> None:
    assert manager.copy_blob_within_bucket("a/src.csv", "../escape.csv") is False
    client.bucket.assert_not_called()


def test_copy_blob_skipped_when_in_error(manager: GcsManager, client: Mock) -> None:
    manager.has_error = True
    assert manager.copy_blob_within_bucket("a/src.csv", "b/dst.csv") is False
    client.bucket.assert_not_called()


@pytest.mark.parametrize(
    "exc, fragment",
    [
        (gexc.NotFound("x"), "Source blob not found"),
        (gexc.PermissionDenied("x"), "Permission denied copying blob"),
        (RuntimeError("x"), "Error copying blob"),
    ],
)
def test_copy_blob_errors_return_false(
    manager: GcsManager, client: Mock, mock_logger: Mock, exc: Exception, fragment: str
) -> None:
    _setup_copy(client, 1, 1)
    client.bucket.return_value.copy_blob.side_effect = exc
    assert manager.copy_blob_within_bucket("a/src.csv", "b/dst.csv") is False
    assert fragment in _error_calls(mock_logger)


# --- list_all_blobs_with_prefix ---


def test_list_all_blobs_with_prefix(manager: GcsManager, client: Mock) -> None:
    client.list_blobs.return_value = _named("p/a", "p/b")
    assert manager.list_all_blobs_with_prefix("p/") == ["p/a", "p/b"]
    client.list_blobs.assert_called_once_with(BUCKET, prefix="p/")


def test_list_all_blobs_default_prefix(manager: GcsManager, client: Mock) -> None:
    client.list_blobs.return_value = []
    assert manager.list_all_blobs_with_prefix() == []
    client.list_blobs.assert_called_once_with(BUCKET, prefix="")


def test_list_all_blobs_skipped_when_in_error(manager: GcsManager, client: Mock) -> None:
    manager.has_error = True
    assert manager.list_all_blobs_with_prefix("p/") == []
    client.list_blobs.assert_not_called()


@pytest.mark.parametrize(
    "exc, fragment",
    [
        (gexc.NotFound("x"), "Bucket not found"),
        (gexc.PermissionDenied("x"), "Permission denied listing blobs"),
        (RuntimeError("x"), "Error listing blobs"),
    ],
)
def test_list_all_blobs_errors_return_empty(
    manager: GcsManager, client: Mock, mock_logger: Mock, exc: Exception, fragment: str
) -> None:
    client.list_blobs.side_effect = exc
    assert manager.list_all_blobs_with_prefix("p/") == []
    assert fragment in _error_calls(mock_logger)


def test_list_all_blobs_retries_error_raised_during_iteration(manager: GcsManager, client: Mock) -> None:
    client.list_blobs.side_effect = [_failing_pages(gexc.DeadlineExceeded("504")), _named("p/a")]
    assert manager.list_all_blobs_with_prefix("p/") == ["p/a"]
    assert client.list_blobs.call_count == 2


def test_copy_blob_retries_transient_error(manager: GcsManager, client: Mock, no_sleep: Mock) -> None:
    _, dst = _setup_copy(client, 50, 50)
    copy_blob = client.bucket.return_value.copy_blob
    copy_blob.side_effect = [gexc.ServiceUnavailable("503"), dst]
    assert manager.copy_blob_within_bucket("a/src.csv", "b/dst.csv") is True
    assert copy_blob.call_count == 2
    no_sleep.assert_called_once()
