#!/usr/bin/env python3
"""
Cleanup script for DataWagon folders/tables created with old naming convention.

This script identifies and removes:
1. GCS folders without version suffixes (e.g., caravan-versioned/claim_raw/)
2. BigQuery tables pointing to those old folders

Usage:
    # Dry run (see what would be deleted)
    python scripts/cleanup_old_naming.py --dry-run

    # Actually delete (with confirmation)
    python scripts/cleanup_old_naming.py

    # Delete without confirmation (dangerous!)
    python scripts/cleanup_old_naming.py --force

Requirements:
    - DW_GCS_PROJECT_ID, DW_GCS_BUCKET, DW_BQ_DATASET set in .env
    - Google Cloud credentials configured
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple

import toml
from dotenv import load_dotenv
from google.cloud import bigquery, storage
from rich.console import Console
from rich.table import Table

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

console = Console()


class OldNamingCleanup:
    """Identifies and removes DataWagon resources using old naming convention."""

    # Pattern to identify version suffixes (e.g., _v1-1, _v2-0)
    VERSION_SUFFIX_PATTERN = re.compile(r"_v\d+-\d+$")

    def __init__(self, project_id: str, bucket_name: str, dataset_id: str, storage_prefix: str):
        """
        Initialize cleanup manager.

        Args:
            project_id: GCS project ID
            bucket_name: GCS bucket name
            dataset_id: BigQuery dataset name
            storage_prefix: Storage prefix (e.g., "caravan-versioned")
        """
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.dataset_id = dataset_id
        self.storage_prefix = storage_prefix.rstrip("/")

        self.storage_client = storage.Client(project=project_id)
        self.bq_client = bigquery.Client(project=project_id)

    def find_bad_folders(self) -> List[str]:
        """
        Find GCS folders WITHOUT version suffixes under storage_prefix.

        Returns:
            List of folder paths (e.g., ["caravan-versioned/claim_raw/"])

        Logic:
            - List all blobs under storage_prefix
            - Extract unique folder paths (first two levels)
            - Filter for folders WITHOUT _vX-Y suffix
            - Exclude folders that are just the prefix itself
        """
        bucket = self.storage_client.bucket(self.bucket_name)
        blobs = bucket.list_blobs(prefix=f"{self.storage_prefix}/")

        folders: Set[str] = set()

        for blob in blobs:
            # Example: caravan-versioned/claim_raw/report_date=2023-06-30/file.csv.gz
            parts = blob.name.split("/")

            if len(parts) < 2:
                continue

            # Get first two levels: caravan-versioned/claim_raw
            if parts[0] == self.storage_prefix and len(parts) >= 2:
                folder_path = f"{parts[0]}/{parts[1]}"
                folders.add(folder_path)

        # Filter for folders WITHOUT version suffix
        bad_folders = []
        for folder in sorted(folders):
            folder_name = folder.split("/")[-1]

            # Skip if it has a version suffix
            if self.VERSION_SUFFIX_PATTERN.search(folder_name):
                continue

            # This is a "bad" folder (no version suffix)
            bad_folders.append(folder)

        return bad_folders

    def find_tables_for_folders(self, folders: List[str]) -> List[Tuple[str, str]]:
        """
        Find BigQuery tables pointing to the given GCS folders.

        Args:
            folders: List of GCS folder paths

        Returns:
            List of (table_name, source_uri) tuples
        """
        dataset_ref = self.bq_client.dataset(self.dataset_id)
        tables = []

        try:
            for table_ref in self.bq_client.list_tables(dataset_ref):
                table = self.bq_client.get_table(table_ref)

                # Only process external tables
                if table.table_type != "EXTERNAL":
                    continue

                if not table.external_data_configuration:
                    continue

                source_uris = table.external_data_configuration.source_uris
                if not source_uris:
                    continue

                # Check if any source URI points to our bad folders
                for uri in source_uris:
                    for folder in folders:
                        if f"gs://{self.bucket_name}/{folder}/" in uri:
                            tables.append((table.table_id, uri))
                            break

        except Exception as e:
            console.print(f"[yellow]Warning: Could not list BigQuery tables: {e}[/yellow]")

        return tables

    def delete_folders(self, folders: List[str], dry_run: bool = True) -> int:
        """
        Delete GCS folders and their contents.

        Args:
            folders: List of folder paths to delete
            dry_run: If True, only show what would be deleted

        Returns:
            Number of blobs deleted (or would be deleted)
        """
        bucket = self.storage_client.bucket(self.bucket_name)
        total_deleted = 0

        for folder in folders:
            prefix = f"{folder}/"
            blobs = list(bucket.list_blobs(prefix=prefix))

            if dry_run:
                console.print(
                    f"[yellow]Would delete {len(blobs)} files from gs://{self.bucket_name}/{folder}/[/yellow]"
                )
                total_deleted += len(blobs)
            else:
                console.print(f"[red]Deleting {len(blobs)} files from gs://{self.bucket_name}/{folder}/...[/red]")
                for blob in blobs:
                    blob.delete()
                    total_deleted += 1
                console.print(f"[green]✓ Deleted {len(blobs)} files[/green]")

        return total_deleted

    def delete_tables(self, tables: List[Tuple[str, str]], dry_run: bool = True) -> int:
        """
        Delete BigQuery tables.

        Args:
            tables: List of (table_name, source_uri) tuples
            dry_run: If True, only show what would be deleted

        Returns:
            Number of tables deleted (or would be deleted)
        """
        deleted = 0

        for table_name, _ in tables:
            table_ref = f"{self.project_id}.{self.dataset_id}.{table_name}"

            if dry_run:
                console.print(f"[yellow]Would drop table: {table_ref}[/yellow]")
            else:
                console.print(f"[red]Dropping table: {table_ref}...[/red]")
                try:
                    self.bq_client.delete_table(table_ref, not_found_ok=True)
                    console.print(f"[green]✓ Dropped table: {table_name}[/green]")
                except Exception as e:
                    console.print(f"[red]✗ Failed to drop {table_name}: {e}[/red]")
                    continue

            deleted += 1

        return deleted


def display_summary(folders: List[str], tables: List[Tuple[str, str]], dry_run: bool):
    """Display summary table of what will be deleted."""
    console.print("\n")
    console.print("[bold cyan]═══ Cleanup Summary ═══[/bold cyan]\n")

    if not folders and not tables:
        console.print("[green]✓ No old naming convention resources found. Nothing to clean up![/green]")
        return

    # Folders table
    if folders:
        folder_table = Table(title="GCS Folders to Delete (without version suffixes)")
        folder_table.add_column("Folder Path", style="cyan")

        for folder in folders:
            folder_table.add_row(folder)

        console.print(folder_table)
        console.print()

    # Tables table
    if tables:
        table_table = Table(title="BigQuery Tables to Drop")
        table_table.add_column("Table Name", style="yellow")
        table_table.add_column("Source URI", style="dim")

        for table_name, source_uri in tables:
            table_table.add_row(table_name, source_uri)

        console.print(table_table)
        console.print()

    # Summary stats
    console.print(f"[bold]Total folders to delete:[/bold] {len(folders)}")
    console.print(f"[bold]Total tables to drop:[/bold] {len(tables)}")

    if dry_run:
        console.print("\n[yellow]This is a DRY RUN - nothing will be deleted[/yellow]")
    else:
        console.print("\n[red bold]⚠️  This will PERMANENTLY delete the above resources![/red bold]")


def confirm_deletion() -> bool:
    """Prompt user to confirm deletion."""
    console.print()
    response = console.input("[bold red]Type 'DELETE' to confirm deletion: [/bold red]")
    return response.strip() == "DELETE"


def load_config_from_toml() -> dict:
    """Load BigQuery config from datawagon-config.toml if it exists."""
    config_path = os.getenv("DW_CSV_SOURCE_TOML", "./datawagon-config.toml")

    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, "r") as f:
            config = toml.load(f)
            return config.get("bigquery", {})
    except Exception as e:
        console.print(f"[yellow]Warning: Could not read {config_path}: {e}[/yellow]")
        return {}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up DataWagon folders/tables created with old naming convention",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt (dangerous!)",
    )
    parser.add_argument(
        "--storage-prefix",
        default=None,
        help="Storage prefix to scan (default: from TOML or 'caravan-versioned')",
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Get config from environment variables
    project_id = os.getenv("DW_GCS_PROJECT_ID")
    bucket_name = os.getenv("DW_GCS_BUCKET")
    dataset_id = os.getenv("DW_BQ_DATASET")

    # If dataset not in env, try to load from TOML config
    bq_config = {}
    if not dataset_id:
        bq_config = load_config_from_toml()
        dataset_id = bq_config.get("dataset")

    # Determine storage prefix (CLI arg > env var > TOML config > default)
    storage_prefix = args.storage_prefix
    if not storage_prefix:
        storage_prefix = os.getenv("DW_BQ_STORAGE_PREFIX")
    if not storage_prefix and bq_config:
        storage_prefix = bq_config.get("storage_prefix")
    if not storage_prefix:
        storage_prefix = "caravan-versioned"

    if not all([project_id, bucket_name, dataset_id]):
        console.print("[red]Error: Missing required configuration[/red]")
        console.print("\nRequired values:")
        console.print(f"  DW_GCS_PROJECT_ID: {'✓' if project_id else '✗ Missing'}")
        console.print(f"  DW_GCS_BUCKET: {'✓' if bucket_name else '✗ Missing'}")
        console.print(f"  DW_BQ_DATASET: {'✓' if dataset_id else '✗ Missing'}")
        console.print("\nSet these in:")
        console.print("  1. .env file (DW_BQ_DATASET=your-dataset)")
        console.print("  2. datawagon-config.toml ([bigquery] section)")
        console.print("  3. Or export as environment variables")
        sys.exit(1)

    console.print("[bold cyan]DataWagon Old Naming Cleanup[/bold cyan]\n")
    console.print(f"Project ID: {project_id}")
    console.print(f"Bucket: {bucket_name}")
    console.print(f"Dataset: {dataset_id}")
    console.print(f"Storage Prefix: {storage_prefix}")
    console.print()

    # Initialize cleanup manager
    cleanup = OldNamingCleanup(project_id, bucket_name, dataset_id, storage_prefix)

    # Find bad resources
    console.print("[cyan]Scanning for folders without version suffixes...[/cyan]")
    bad_folders = cleanup.find_bad_folders()

    console.print("[cyan]Finding BigQuery tables pointing to old folders...[/cyan]")
    bad_tables = cleanup.find_tables_for_folders(bad_folders)

    # Display summary
    display_summary(bad_folders, bad_tables, args.dry_run)

    if not bad_folders and not bad_tables:
        sys.exit(0)

    # Confirm deletion
    if not args.dry_run:
        if not args.force:
            if not confirm_deletion():
                console.print("[yellow]Deletion cancelled[/yellow]")
                sys.exit(0)

    # Perform deletion
    console.print("\n[bold cyan]═══ Starting Cleanup ═══[/bold cyan]\n")

    # Drop tables first (safer to drop tables before deleting data)
    if bad_tables:
        console.print("[cyan]Step 1: Dropping BigQuery tables...[/cyan]")
        tables_deleted = cleanup.delete_tables(bad_tables, dry_run=args.dry_run)
        console.print(f"[green]✓ Processed {tables_deleted} tables[/green]\n")

    # Delete folders
    if bad_folders:
        console.print("[cyan]Step 2: Deleting GCS folders...[/cyan]")
        files_deleted = cleanup.delete_folders(bad_folders, dry_run=args.dry_run)
        console.print(f"[green]✓ Processed {files_deleted} files[/green]\n")

    # Final message
    if args.dry_run:
        console.print("\n[yellow bold]DRY RUN COMPLETE[/yellow bold]")
        console.print("Run without --dry-run to actually delete these resources")
    else:
        console.print("\n[green bold]✓ CLEANUP COMPLETE[/green bold]")
        console.print("\nNext steps:")
        console.print("1. Re-upload files: [cyan]datawagon compare-local-to-bucket upload-to-gcs[/cyan]")
        console.print("2. Create tables: [cyan]datawagon create-bigquery-tables[/cyan]")


if __name__ == "__main__":
    main()
