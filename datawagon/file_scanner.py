from pathlib import Path
from typing import List


class FileScanner:
    def __init__(self) -> None:
        pass

    def scan_for_csv_files(self, source_path: Path) -> List[Path]:
        return list(source_path.glob("**/*.csv.gz"))
