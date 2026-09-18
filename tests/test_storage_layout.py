"""Tests for StorageLayout: Report Type + Version <-> Storage Folder, blob path, Table."""

from pathlib import Path
from typing import Any, Optional

import pytest

from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.source_config import SourceConfig, SourceFromLocalFS
from datawagon.objects.storage_layout import Location, StorageLayout, Stray, Table

LAYOUT = StorageLayout(prefix="caravan-versioned", report_types=frozenset({"claim_raw", "adj_claim_raw"}))


def _file(
    file_name: str = "YouTube_CaravanInc_M_20230601_claim_raw_v1-1.csv.gz",
    report_type: str = "claim_raw",
    report_date_str: Optional[str] = "2023-06-30",
) -> ManagedFileMetadata:
    return ManagedFileMetadata(
        file_name=file_name,
        file_path=Path(f"/data/{file_name}"),
        base_name=report_type,
        report_type=report_type,
        table_name=report_type,
        file_dir="/data",
        content_owner="CaravanInc",
        report_date_key=20230630 if report_date_str else None,
        report_date_str=report_date_str,
        file_version=StorageLayout.version_of(file_name),
        file_size_in_bytes=1,
        file_size="1 B",
    )


def test_blob_path() -> None:
    assert LAYOUT.blob_path(_file()) == (
        "caravan-versioned/claim_raw_v1-1/report_date=2023-06-30/" "YouTube_CaravanInc_M_20230601_claim_raw_v1-1.csv.gz"
    )


@pytest.mark.parametrize("report_type", ["claim_raw", "adj_claim_raw"])
def test_round_trip(report_type: str) -> None:
    f = _file(f"YouTube_CaravanInc_M_20230601_{report_type}_v1-1.csv.gz", report_type)
    assert LAYOUT.locate(LAYOUT.blob_path(f)) == Location(report_type, "v1-1", "2023-06-30")


def test_table() -> None:
    assert LAYOUT.table("claim_raw", "v1-1") == Table("claim_raw_v1_1", "caravan-versioned/claim_raw_v1-1")


@pytest.mark.parametrize("version", ["v1", "v1-1", "v12-30"])
def test_table_named_inverts_table(version: str) -> None:
    table = LAYOUT.table("adj_claim_raw", version)
    assert LAYOUT.table_named(table.name) == table


@pytest.mark.parametrize("name", ["claim_raw", "unknown_v1_1", "claim_raw_v1_1_1"])
def test_table_named_rejects_unknown_names(name: str) -> None:
    assert LAYOUT.table_named(name) is None


def test_version_of() -> None:
    assert StorageLayout.version_of("YouTube_X_M_20230601_claim_raw_v1-1.csv.gz") == "v1-1"
    assert StorageLayout.version_of("YouTube_X_M_20230601_claim_raw.csv.gz") == ""


@pytest.mark.parametrize(
    "blob, folder",
    [
        (
            "caravan-versioned/claim_raw/report_date=2025-12-31/f_v1-1.csv.gz",
            "caravan-versioned/claim_raw",
        ),  # no Version
        (
            "caravan-versioned/video_raw_v1-1/report_date=2025-12-31/f.csv.gz",
            "caravan-versioned/video_raw_v1-1",
        ),  # unknown type
        ("caravan-versioned/claim_raw_v1-1/f.csv.gz", "caravan-versioned/claim_raw_v1-1"),  # no Report Month
        (
            "caravan-versioned/claim_raw_v1-1/report_date=2025-12-31/f.csv",
            "caravan-versioned/claim_raw_v1-1",
        ),  # not .csv.gz
        ("other/claim_raw_v1-1/report_date=2025-12-31/f.csv.gz", "other/claim_raw_v1-1"),  # outside prefix
        (
            "caravan-versioned-old/claim_raw_v1-1/report_date=2025-12-31/f.csv.gz",
            "caravan-versioned-old/claim_raw_v1-1",
        ),
    ],
)
def test_locate_strays(blob: str, folder: str) -> None:
    assert LAYOUT.locate(blob) == Stray(folder)


@pytest.mark.parametrize(
    "file",
    [
        _file("YouTube_CaravanInc_M_20230601_claim_raw.csv.gz"),  # no Version
        _file(report_date_str=None),  # no Report Month
        _file("YouTube_CaravanInc_M_20230601_claim_raw_v1-1.csv"),  # not .csv.gz
        _file(report_type="video_raw"),  # unknown Report Type
    ],
)
def test_blob_path_rejects(file: ManagedFileMetadata) -> None:
    with pytest.raises(ValueError):
        LAYOUT.blob_path(file)


def _config(**overrides: str) -> SourceConfig:
    fields: dict[str, Any] = {"is_enabled": True, "select_file_name_base": "claim_raw", **overrides}
    return SourceConfig(file={"claim_raw": SourceFromLocalFS(**fields)})


def test_from_config() -> None:
    layout = StorageLayout.from_config(_config(), "caravan-versioned")
    assert layout == StorageLayout("caravan-versioned", frozenset({"claim_raw"}))


def test_from_config_accepts_matching_legacy_keys() -> None:
    config = _config(storage_folder_name="caravan-versioned/claim_raw", table_name="claim_raw")
    StorageLayout.from_config(config, "caravan-versioned")


@pytest.mark.parametrize(
    "overrides",
    [{"storage_folder_name": "caravan/claim_raw"}, {"table_name": "claims"}],
)
def test_from_config_rejects_disagreeing_legacy_keys(overrides: dict[str, str]) -> None:
    with pytest.raises(ValueError, match=r"\[file\.claim_raw\]"):
        StorageLayout.from_config(_config(**overrides), "caravan-versioned")
