#!/usr/bin/env python3
"""
Utility to remove empty GCS folder markers.

After deleting all files from a folder, GCS may still show the folder in the
console if folder marker objects exist (blobs that end with `/`).

This script removes those marker objects.

Usage:
    # Remove specific folders
    python scripts/remove_folder_markers.py caravan-versioned/claim_raw caravan-versioned/ownership_raw

    # Dry run
    python scripts/remove_folder_markers.py --dry-run caravan-versioned/claim_raw

    # Or use the wrapper
    ./scripts/cleanup.sh --dry-run  # Handles this automatically
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import storage
from rich.console import Console

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

console = Console()


def load_config():
    """Load configuration from .env and TOML."""
    load_dotenv()

    project_id = os.getenv("DW_GCS_PROJECT_ID")
    bucket_name = os.getenv("DW_GCS_BUCKET")

    if not all([project_id, bucket_name]):
        console.print("[red]Error: Missing required environment variables[/red]")
        console.print("Required: DW_GCS_PROJECT_ID, DW_GCS_BUCKET")
        sys.exit(1)

    return project_id, bucket_name


def remove_folder_markers(project_id: str, bucket_name: str, folders: list[str], dry_run: bool = True) -> int:
    """Remove folder marker objects from GCS."""
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    removed = 0

    for folder in folders:
        # Ensure folder path ends with /
        marker_path = folder if folder.endswith("/") else f"{folder}/"

        marker_blob = bucket.blob(marker_path)

        try:
            if marker_blob.exists():
                if dry_run:
                    console.print(f"[yellow]Would remove: gs://{bucket_name}/{marker_path}[/yellow]")
                else:
                    marker_blob.delete()
                    console.print(f"[green]✓ Removed: gs://{bucket_name}/{marker_path}[/green]")
                removed += 1
            else:
                console.print(f"[dim]Not found: gs://{bucket_name}/{marker_path}[/dim]")
        except Exception as e:
            console.print(f"[red]✗ Error checking {marker_path}: {e}[/red]")

    return removed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Remove empty GCS folder markers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Remove specific folders (dry run)
  python scripts/remove_folder_markers.py --dry-run caravan-versioned/claim_raw

  # Actually remove
  python scripts/remove_folder_markers.py caravan-versioned/claim_raw caravan-versioned/ownership_raw

  # Remove multiple folders
  python scripts/remove_folder_markers.py caravan-versioned/*_raw
        """,
    )
    parser.add_argument("folders", nargs="+", help="Folder paths to remove (e.g., caravan-versioned/claim_raw)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")

    args = parser.parse_args()

    project_id, bucket_name = load_config()

    console.print("[bold cyan]Remove GCS Folder Markers[/bold cyan]\n")
    console.print(f"Project: {project_id}")
    console.print(f"Bucket: {bucket_name}")
    console.print(f"Folders: {len(args.folders)}")
    console.print()

    if args.dry_run:
        console.print("[yellow]DRY RUN MODE[/yellow]\n")

    removed = remove_folder_markers(project_id, bucket_name, args.folders, args.dry_run)

    console.print()
    if removed > 0:
        if args.dry_run:
            console.print(f"[yellow]Would remove {removed} folder markers[/yellow]")
            console.print("Run without --dry-run to actually remove them")
        else:
            console.print(f"[green]✓ Removed {removed} folder markers[/green]")
    else:
        console.print("[dim]No folder markers found[/dim]")


if __name__ == "__main__":
    main()
