from typing import List

import click

from datawagon.bucket.gcs_manager import GcsManager
from datawagon.console import error, info, newline
from datawagon.objects.app_config import AppConfig
from datawagon.objects.current_table_data import CurrentDestinationData
from datawagon.objects.source_config import SourceConfig


@click.command()
@click.pass_context
def files_in_storage(ctx: click.Context) -> List[CurrentDestinationData]:
    """Display existing tables and number of rows."""

    app_config: AppConfig = ctx.obj["CONFIG"]
    gcs_manager = GcsManager(app_config.gcs_project_id, app_config.gcs_bucket)

    if gcs_manager.has_error:
        error("Unable to connect to GCS. Check credentials and try again.")
        ctx.abort()
    else:
        ctx.obj["GCS_MANAGER"] = gcs_manager

    valid_config: SourceConfig = ctx.obj["FILE_CONFIG"]

    blob_df = gcs_manager.files_in_blobs_df(valid_config)

    all_table_data = []
    for base_name in blob_df["base_name"].unique():
        table_files = blob_df.loc[blob_df["base_name"] == base_name]._file_name.tolist()

        all_table_data.append(
            CurrentDestinationData(
                base_name=base_name,
                file_count=len(table_files),
                source_files=table_files,
            )
        )

    file_count = len(blob_df)

    newline()
    info(f"{file_count} files in bucket storage", bold=True)
    newline()

    return all_table_data
