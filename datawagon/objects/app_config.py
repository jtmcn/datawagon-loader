from pathlib import Path

from pydantic import BaseModel


class AppConfig(BaseModel):
    csv_source_dir: Path
    csv_source_config: Path
    gcs_project_id: str
    gcs_bucket: str
