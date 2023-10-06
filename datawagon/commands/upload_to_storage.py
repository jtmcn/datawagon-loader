# from pathlib import Path
from typing import List

import click

from datawagon.bucket.gcs_manager import GcsManager
from datawagon.commands.compare import compare_local_files_to_bucket
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import ManagedFilesToDatabase


@click.command(name="upload")
@click.pass_context
def upload_all_gzip_csv(ctx: click.Context) -> None:
    """Upload all new files to storage bucket."""

    matched_new_files: List[ManagedFilesToDatabase] = ctx.invoke(
        compare_local_files_to_bucket
    )
    gcs_manager: GcsManager = ctx.obj["GCS_MANAGER"]

    csv_file_infos: List[ManagedFileMetadata] = [
        file_info for src in matched_new_files for file_info in src.files
    ]

    if len(csv_file_infos) != 0:
        click.echo(nl=True)
        click.echo(nl=True)

        click.confirm(
            f"Upload {len(csv_file_infos)} new files?", default=False, abort=True
        )

        click.echo(nl=True)

        has_errors = False
        for csv_info in csv_file_infos:
            click.echo(
                f"Uploading {csv_info.file_name_without_extension} into {csv_info.storage_folder_name}... ",
                nl=False,
            )

            str_path = str(csv_info.file_path)

            if csv_info.report_date_key:
                destination_name = (
                    f"{csv_info.storage_folder_name or csv_info.base_name}/"
                    + f"report_date_key={csv_info.report_date_key}/{csv_info.file_name}"
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
                click.echo(nl=True)
                click.secho(f"Upload failed for {csv_info.file_name}", fg="red")
            else:
                click.secho("Success", fg="green")

        if has_errors:
            click.secho("Import errors, check output", fg="red", bold=True)
        else:
            click.secho(
                "Successfully uploaded files into storage bucket",
                fg="green",
            )
