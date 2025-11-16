from typing import List, Tuple

import click
from tabulate import tabulate

from datawagon.bucket.gcs_manager import GcsManager
from datawagon.commands.compare import compare_local_files_to_bucket
from datawagon.exceptions import GcsOperationError
from datawagon.logging_config import get_logger
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.managed_file_scanner import ManagedFilesToDatabase


@click.command(name="upload-to-gcs")
@click.pass_context
def upload_all_gzip_csv(ctx: click.Context) -> None:
    """Upload all new files to storage bucket."""
    logger = get_logger("upload")

    matched_new_files: List[ManagedFilesToDatabase] = ctx.invoke(
        compare_local_files_to_bucket
    )
    gcs_manager: GcsManager = ctx.obj["GCS_MANAGER"]

    csv_file_infos: List[ManagedFileMetadata] = [
        file_info for src in matched_new_files for file_info in src.files
    ]

    if not csv_file_infos:
        click.secho("No new files to upload.", fg="yellow")
        return

    click.echo(nl=True)
    click.confirm(f"Upload {len(csv_file_infos)} new files?", default=False, abort=True)
    click.echo(nl=True)

    results: List[Tuple[str, str, str]] = []
    has_errors = False

    for csv_info in csv_file_infos:
        try:
            destination_name = _build_destination_name(csv_info)
            gcs_manager.upload_blob(str(csv_info.file_path), destination_name)
            results.append((csv_info.file_name, "Success", ""))
        except GcsOperationError as e:
            has_errors = True
            error_message = f"Upload failed: {e}"
            results.append((csv_info.file_name, "Failed", error_message))
            logger.error(f"Upload failed for {csv_info.file_name}: {e}")
        except Exception as e:
            has_errors = True
            error_message = f"An unexpected error occurred: {e}"
            results.append((csv_info.file_name, "Failed", error_message))
            logger.error(f"Unexpected error uploading {csv_info.file_name}: {e}")

    _display_upload_results(results)

    if has_errors:
        click.secho("\nUpload process completed with errors.", fg="red", bold=True)
    else:
        click.secho(
            "\nSuccessfully uploaded all new files.",
            fg="green",
        )


def _build_destination_name(csv_info: ManagedFileMetadata) -> str:
    if csv_info.report_date_str:
        return (
            f"{csv_info.storage_folder_name or csv_info.base_name}/"
            + f"report_date={csv_info.report_date_str}/{csv_info.file_name}"
        )
    else:
        return (
            f"{csv_info.storage_folder_name or csv_info.base_name}/"
            + csv_info.file_name
        )


def _display_upload_results(results: List[Tuple[str, str, str]]) -> None:
    headers = ["File Name", "Status", "Details"]
    click.echo(tabulate(results, headers=headers, tablefmt="grid"))
