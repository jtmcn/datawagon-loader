# from pathlib import Path
from typing import List

import click

from datawagon.bucket.gcs_manager import GcsManager
from datawagon.commands.compare import compare_local_files_to_bucket
from datawagon.console import (confirm, error, inline_status_end,
                               inline_status_start, newline, success)
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import ManagedFilesToDatabase


@click.command(name="upload-to-gcs")
@click.pass_context
def upload_all_gzip_csv(ctx: click.Context) -> None:
    """Upload all new files to storage bucket."""

    matched_new_files: List[ManagedFilesToDatabase] = ctx.invoke(
        compare_local_files_to_bucket
    )

    # FIX: Lazy initialization with error handling
    gcs_manager = ctx.obj.get("GCS_MANAGER")
    if not gcs_manager:
        from datawagon.objects.app_config import AppConfig
        app_config: AppConfig = ctx.obj["CONFIG"]
        gcs_manager = GcsManager(app_config.gcs_project_id, app_config.gcs_bucket)
        if gcs_manager.has_error:
            error("Failed to connect to GCS. Check credentials and project settings.")
            ctx.abort()
        ctx.obj["GCS_MANAGER"] = gcs_manager

    csv_file_infos: List[ManagedFileMetadata] = [
        file_info for src in matched_new_files for file_info in src.files
    ]

    if len(csv_file_infos) != 0:
        newline()
        newline()

        confirm(f"Upload {len(csv_file_infos)} new files?", default=False, abort=True)

        newline()

        has_errors = False
        for csv_info in csv_file_infos:
            inline_status_start(
                f"Uploading {csv_info.file_name} into {csv_info.storage_folder_name}..."
            )

            str_path = str(csv_info.file_path)

            if csv_info.report_date_str:
                destination_name = (
                    f"{csv_info.storage_folder_name or csv_info.base_name}/"
                    + f"report_date={csv_info.report_date_str}/{csv_info.file_name}"
                )
            else:
                destination_name = (
                    (csv_info.storage_folder_name or csv_info.base_name)
                    + "/"
                    + csv_info.file_name
                )

            is_success = gcs_manager.upload_blob(
                str_path,
                destination_name,
            )

            if not is_success:
                has_errors = True
                inline_status_end(False, error_msg=f"Failed: {csv_info.file_name}")
            else:
                inline_status_end(True)

        if has_errors:
            error("Import errors, check output")
        else:
            success("Successfully uploaded files into storage bucket")
