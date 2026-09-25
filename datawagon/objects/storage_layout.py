"""Where report files live in the bucket, and which Table reads them.

One Storage Folder per Report Type and Version (ADR-0001), partitioned by Report Month:
``{prefix}/{report_type}_{version}/report_date={YYYY-MM-DD}/{file_name}``, read by Table
``{report_type}_{version with - as _}``.
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple, Optional

from datawagon.logging_config import get_logger

if TYPE_CHECKING:
    from datawagon.objects.managed_file_metadata import ManagedFileMetadata
    from datawagon.objects.source_config import SourceConfig

logger = get_logger(__name__)

DEFAULT_STORAGE_PREFIX = "caravan-versioned"
_VERSION = r"v\d+(?:-\d+)?"
_FILE_VERSION = re.compile(rf"_({_VERSION})")
_FOLDER = re.compile(rf"^(.+)_({_VERSION})$")
_TABLE = re.compile(r"^(.+)_v(\d+)(?:_(\d+))?$")
_PARTITION = re.compile(r"^report_date=(\d{4}-\d{2}-\d{2})$")
_EXTENSION = ".csv.gz"


class Location(NamedTuple):
    report_type: str
    version: str
    report_month: str  # month-end date, YYYY-MM-DD


class Stray(NamedTuple):
    """A blob outside any Storage Folder; ``folder`` is its bucket path up to the partition or file."""

    folder: str


class Table(NamedTuple):
    name: str
    folder: str


@dataclass(frozen=True)
class StorageLayout:
    prefix: str
    report_types: frozenset[str]

    @classmethod
    def from_config(cls, config: "SourceConfig", prefix: str) -> "StorageLayout":
        """Report Types are the ``[file.X]`` keys; deprecated per-file names must agree with them."""
        for key, source in config.file.items():
            for field, derived in [("storage_folder_name", f"{prefix}/{key}"), ("table_name", key)]:
                value = getattr(source, field)
                if not value:
                    continue
                if value != derived:
                    raise ValueError(f"[file.{key}] {field} = {value!r} disagrees with the derived {derived!r}")
                logger.warning(f"[file.{key}] {field} is deprecated and can be removed")
        return cls(prefix, frozenset(config.file))

    @staticmethod
    def version_of(file_name: str) -> str:
        """``..._claim_raw_v1-1.csv.gz`` -> ``v1-1``; empty when the name has no Version."""
        match = _FILE_VERSION.search(file_name)
        return match.group(1) if match else ""

    def table(self, report_type: str, version: str) -> Table:
        return Table(f"{report_type}_{version.replace('-', '_')}", f"{self.prefix}/{report_type}_{version}")

    def table_named(self, name: str) -> Optional[Table]:
        match = _TABLE.match(name)
        if not match or match.group(1) not in self.report_types:
            return None
        report_type, major, minor = match.groups()
        return self.table(report_type, f"v{major}-{minor}" if minor else f"v{major}")

    def blob_path(self, file: "ManagedFileMetadata") -> str:
        """Raises ValueError for files no Table could read."""
        if file.report_type not in self.report_types:
            raise ValueError(f"{file.file_name}: unknown Report Type {file.report_type!r}")
        if not file.file_version:
            raise ValueError(f"{file.file_name}: no Version in file name")
        if not file.report_date_str:
            raise ValueError(f"{file.file_name}: no Report Month in file name")
        # Hive-partitioned tables read every file in the folder, so only .csv.gz may land there
        if not file.file_name.endswith(_EXTENSION):
            raise ValueError(f"{file.file_name}: only {_EXTENSION} files can be uploaded")
        folder = self.table(file.report_type, file.file_version).folder
        return f"{folder}/report_date={file.report_date_str}/{file.file_name}"

    def locate(self, blob_name: str) -> Location | Stray:
        all_parts = blob_name.split("/")
        partition = next((i for i, p in enumerate(all_parts) if p.startswith("report_date=")), len(all_parts) - 1)
        stray = Stray("/".join(all_parts[:partition]))

        if not blob_name.startswith(f"{self.prefix}/"):
            return stray
        parts = blob_name.removeprefix(f"{self.prefix}/").split("/")
        if len(parts) != 3 or not parts[2].endswith(_EXTENSION):
            return stray
        folder, month = _FOLDER.match(parts[0]), _PARTITION.match(parts[1])
        if not folder or not month or folder.group(1) not in self.report_types:
            return stray
        return Location(folder.group(1), folder.group(2), month.group(1))
