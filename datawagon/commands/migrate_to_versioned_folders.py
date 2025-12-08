import os
from dataclasses import dataclass
from typing import List

import click

from datawagon.bucket.gcs_manager import GcsManager
from datawagon.console import (
    confirm,
    error,
    header,
    info,
    newline,
    panel,
    progress_bar,
    success,
    warning,
)
from datawagon.objects.managed_file_metadata import ManagedFileMetadata
from datawagon.objects.source_config import SourceConfig

# Constants for root folder migration
OLD_ROOT_FOLDER = "caravan"  # Where files currently exist
NEW_ROOT_FOLDER = "caravan-versioned"  # Where files should be migrated to


@dataclass
class MigrationItem:
    """Represents a single file to migrate."""

    source_path: str
    destination_path: str
    file_version: str
    base_name: str
    file_size_mb: float
    needs_migration: bool
    skip_reason: str | None = None


def build_migration_plan(
    gcs_manager: GcsManager, source_config: SourceConfig
) -> List[MigrationItem]:
    """Build migration plan by scanning GCS bucket for files needing reorganization.

    Scans all files in the GCS bucket and identifies which files need to be
    migrated to version-based folder structure. Skips files already in correct
    location or without version information.

    Args:
        gcs_manager: GCS manager for bucket operations
        source_config: Source configuration with file patterns

    Returns:
        List of MigrationItem objects with migration plan
    """

    migration_items: List[MigrationItem] = []

    # For each configured file type
    for file_id, file_source in source_config.file.items():
        if not file_source.is_enabled:
            continue

        # Config now has "caravan-versioned/claim_raw"
        storage_folder = (
            file_source.storage_folder_name or file_source.select_file_name_base
        )

        # Convert to source prefix (where files currently are)
        # Replace "caravan-versioned" with "caravan" to find existing files
        source_folder = storage_folder.replace(NEW_ROOT_FOLDER, OLD_ROOT_FOLDER)

        # List all files from OLD location
        prefix = f"{source_folder}/"
        blob_names = gcs_manager.list_all_blobs_with_prefix(prefix)

        for blob_name in blob_names:
            # Extract filename from full path
            filename = os.path.basename(blob_name)

            # Extract version from filename
            file_version = ManagedFileMetadata.get_file_version(filename)

            # Determine if migration is needed
            needs_migration = False
            skip_reason = None

            if not file_version:
                skip_reason = "No version in filename"
            elif f"_{file_version}/" in blob_name:
                skip_reason = "Already in versioned folder"
            elif NEW_ROOT_FOLDER in blob_name:
                skip_reason = "Already in new root folder (caravan-versioned)"
            else:
                needs_migration = True

            # Build destination path
            if needs_migration:
                # Replace OLD root with NEW root and add version
                # Example: caravan/claim_raw/report_date=2025-07-31/file_v1-1.csv.gz
                #       -> caravan-versioned/claim_raw_v1-1/report_date=2025-07-31/file_v1-1.csv.gz

                path_parts = blob_name.split("/")

                # Replace folder name with versioned folder name
                if len(path_parts) >= 2:
                    # Handle multi-level storage folders like "caravan/claim_raw"
                    if "/" in source_folder:
                        folder_parts = source_folder.split("/")
                        # Replace first part with new root
                        folder_parts[0] = NEW_ROOT_FOLDER
                        # Add version to last part of storage folder
                        folder_parts[-1] = f"{folder_parts[-1]}_{file_version}"
                        versioned_folder = "/".join(folder_parts)

                        # Replace storage folder in path
                        for i, part in enumerate(folder_parts):
                            if i < len(path_parts):
                                path_parts[i] = folder_parts[i]
                    else:
                        # Single-level folder like "test"
                        path_parts[0] = f"{NEW_ROOT_FOLDER}_{file_version}"

                    destination_path = "/".join(path_parts)
                else:
                    destination_path = f"{storage_folder}_{file_version}/{filename}"
            else:
                destination_path = blob_name

            # Get file size (would need to fetch blob metadata)
            # For now, use 0 as placeholder
            file_size_mb = 0.0

            migration_items.append(
                MigrationItem(
                    source_path=blob_name,
                    destination_path=destination_path,
                    file_version=file_version or "",
                    base_name=file_source.select_file_name_base,
                    file_size_mb=file_size_mb,
                    needs_migration=needs_migration,
                    skip_reason=skip_reason,
                )
            )

    return migration_items


def display_migration_plan(migration_items: List[MigrationItem]):
    """Display migration plan in a readable format with counts and examples.

    Presents migration plan to user showing files to be migrated,
    files to be skipped, and reasons for skipping. Displays source and
    destination paths for clarity.

    Args:
        migration_items: List of migration items from build_migration_plan()
    """

    needs_migration = [item for item in migration_items if item.needs_migration]
    skipped = [item for item in migration_items if not item.needs_migration]

    newline()
    header("MIGRATION PLAN", style="cyan")
    newline()

    info(f"Total files scanned: {len(migration_items)}")
    success(f"Files to migrate: {len(needs_migration)}")
    warning(f"Files to skip: {len(skipped)}")

    # Show files to migrate
    if needs_migration:
        newline()
        header(f"FILES TO MIGRATE ({len(needs_migration)})", style="green")

        # Group by base_name
        by_base_name = {}
        for item in needs_migration:
            if item.base_name not in by_base_name:
                by_base_name[item.base_name] = []
            by_base_name[item.base_name].append(item)

        for base_name, items in sorted(by_base_name.items()):
            newline()
            info(f"{base_name}: {len(items)} files", bold=True)

            # Show first few examples
            for item in items[:3]:
                info(f"  FROM: {item.source_path}")
                info(f"  TO:   {item.destination_path}")
                newline()

            if len(items) > 3:
                info(f"  ... and {len(items) - 3} more files")

    # Show skipped files summary
    if skipped:
        newline()
        header(f"SKIPPED ({len(skipped)})", style="yellow")

        skip_reasons = {}
        for item in skipped:
            reason = item.skip_reason or "Unknown"
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

        for reason, count in sorted(skip_reasons.items()):
            info(f"  {reason}: {count} files")


def execute_migration(
    gcs_manager: GcsManager, migration_items: List[MigrationItem], batch_size: int
):
    """Execute the migration plan by copying files to version-based folders.

    Copies files from old location to new version-based folder structure in
    batches. Shows progress with status updates for each batch.

    Args:
        gcs_manager: GCS manager for bucket operations
        migration_items: List of migration items to execute
        batch_size: Number of files to process per batch
    """

    to_migrate = [item for item in migration_items if item.needs_migration]

    newline()
    header("EXECUTING MIGRATION", style="cyan")
    newline()

    success_count = 0
    error_count = 0

    with progress_bar(to_migrate, "Migrating files") as progress:
        task = progress.add_task("Migrating files", total=len(to_migrate))
        for item in to_migrate:
            success_result = gcs_manager.copy_blob_within_bucket(
                item.source_path, item.destination_path
            )

            if success_result:
                success_count += 1
            else:
                error_count += 1
                error(f"Error migrating: {item.source_path}")

            progress.advance(task)

    # Summary
    newline()
    header("MIGRATION COMPLETE", style="cyan")
    newline()

    success(f"Successfully migrated: {success_count}")
    if error_count > 0:
        error(f"Errors: {error_count}")

    newline()
    panel(
        "1. Verify files in new locations using: datawagon files-in-storage\n"
        "2. Update BigQuery external table URIs to point to versioned folders\n"
        "3. Test BigQuery queries against new table locations\n"
        "4. Once verified, manually delete original files from GCS",
        title="Next Steps",
        style="cyan",
        border_style="cyan",
    )


@click.command(name="migrate-to-versioned-folders")
@click.option(
    "--dry-run/--execute",
    default=True,
    help="Show plan without executing (default: dry-run)",
)
@click.option(
    "--batch-size", default=100, help="Files to process per batch (default: 100)"
)
@click.pass_context
def migrate_to_versioned_folders(ctx: click.Context, dry_run: bool, batch_size: int):
    """Migrate existing GCS files to version-based folder structure."""

    # Get GCS manager and config
    from datawagon.objects.app_config import AppConfig

    app_config: AppConfig = ctx.obj["CONFIG"]
    gcs_manager = GcsManager(app_config.gcs_project_id, app_config.gcs_bucket)

    if not gcs_manager:
        ctx.abort()

    source_config: SourceConfig = ctx.obj["FILE_CONFIG"]

    # Scan bucket for all files
    migration_plan = build_migration_plan(gcs_manager, source_config)

    # Display plan
    display_migration_plan(migration_plan)

    # If execute mode, confirm and migrate
    if not dry_run:
        needs_migration_count = sum(
            1 for item in migration_plan if item.needs_migration
        )
        if needs_migration_count > 0:
            click.echo("\n")
            if click.confirm(f"Migrate {needs_migration_count} files?"):
                execute_migration(gcs_manager, migration_plan, batch_size)
        else:
            click.secho("\nNo files to migrate.", fg="yellow")
