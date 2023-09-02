from pathlib import Path

from pydantic import BaseModel


class AppConfig(BaseModel):
    db_schema: str
    db_url: str
    csv_source_dir: Path
    csv_source_config: Path
