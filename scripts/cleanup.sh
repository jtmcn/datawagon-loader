#!/bin/bash
#
# Wrapper script to run cleanup_old_naming.py with proper environment
#
# Usage:
#   ./scripts/cleanup.sh --dry-run    # Preview what would be deleted
#   ./scripts/cleanup.sh              # Delete with confirmation
#   ./scripts/cleanup.sh --force      # Delete without confirmation
#

set -e

# Change to project root directory
cd "$(dirname "$0")/.."

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "Error: .venv directory not found"
    echo "Run: make setup  OR  ./setup-venv.sh"
    exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    echo "Create .env with required variables:"
    echo "  DW_GCS_PROJECT_ID=your-project-id"
    echo "  DW_GCS_BUCKET=your-bucket-name"
    echo "  DW_BQ_DATASET=your-dataset-name"
    exit 1
fi

# Run the cleanup script with all arguments passed through
python scripts/cleanup_old_naming.py "$@"
