# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DataWagon automates loading YouTube Analytics CSV files into Google Cloud Storage buckets. It processes compressed files (.csv.gz, .csv.zip), validates file names against regex patterns, extracts metadata, and uploads to GCS with partitioning by report date.

## Development Commands

### Environment Setup

DataWagon supports two installation methods:

#### Method 1: Poetry (Recommended for Development)

**Use this if you:**
- Want to contribute to DataWagon
- Need to modify dependencies
- Want full development tooling (mypy, black, flake8, pytest)
- Plan to run tests and code quality checks

**First-time setup:**
```bash
make setup               # Detects Poetry and runs full setup
# OR explicitly:
make setup-poetry        # Poetry-specific setup
source .venv/bin/activate
```

**Updating environment:**
```bash
./update.sh              # Pull changes and update with Poetry
# OR manually:
git pull
poetry install
make requirements
```

#### Method 2: Standard Python Virtual Environment (Runtime Only)

**Use this if you:**
- Just want to run DataWagon
- Don't need development tools
- Want faster, lighter installation
- Don't plan to modify dependencies

**Important:** This installs runtime dependencies only (no mypy, black, flake8, pytest).

**First-time setup:**
```bash
# Unix (macOS/Linux)
./setup-venv.sh

# Windows
setup-venv.bat
```

**Updating environment:**
```bash
# Unix (macOS/Linux)
./update-venv.sh

# Windows
update-venv.bat
```

**Verifying Installation (Both Methods):**
```bash
# Unix
source .venv/bin/activate

# Windows
.venv\Scripts\activate.bat

# Then run (works on all platforms after activation)
datawagon --help
make test  # Note: make requires Unix; Windows users should use Poetry for tests
```

### Code Quality (Pre-commit Checks)

The Makefile automatically detects whether you're using Poetry or a standard venv:

```bash
make pre-commit          # Run all checks (type, isort, format, lint, test, requirements-check)
make pre-commit-fast     # Run faster checks (type, lint, test only)
make type                # Type check with mypy
make isort               # Sort imports
make format              # Format code with black
make lint                # Lint with flake8
make vulture             # Detect dead code (optional)
make test                # Run tests with pytest
make requirements-check  # Verify requirements.txt is in sync with poetry.lock
```

**Note:** If using Poetry, these run via `poetry run`. Otherwise, they use your active virtual environment.

### Testing
```bash
make test                # Run all tests
make test-cov            # Run tests with HTML coverage report
poetry run pytest tests/ --quiet
poetry run pytest tests/file_utils_test.py -k test_group_by_base_name  # Run single test
```

### Build & Install
```bash
make build-app           # Build with poetry
poetry build
```

### Running the Application
```bash
datawagon --help                     # Show available commands
datawagon files-in-local-fs          # List files in source directory
datawagon compare-local-to-bucket    # Compare local files to GCS bucket
datawagon upload-to-gcs              # Upload new files to GCS
datawagon file-zip-to-gzip           # Convert .zip files to .gzip
datawagon files-in-storage           # List files in GCS bucket
```

Commands can be chained:
```bash
datawagon files-in-local-fs compare-local-to-bucket upload-to-gcs
```

## Architecture

### Configuration System

**Source Configuration (`datawagon-config.toml`)**: Defines file types to process. Each `[file.{name}]` section specifies:
- `select_file_name_base`: Pattern to match files
- `exclude_file_name_base`: Pattern to exclude files
- `regex_pattern`: Regex to extract metadata from filenames
- `regex_group_names`: Named groups from regex (e.g., `["content_owner", "file_date_key"]`)
- `storage_folder_name`: GCS destination folder
- `table_name`: Destination table name
- `table_append_or_replace`: Upload strategy

**Runtime Configuration**: Via environment variables or CLI flags:
- `DW_CSV_SOURCE_DIR`: Source directory for CSV files
- `DW_CSV_SOURCE_TOML`: Path to source config TOML
- `DW_GCS_PROJECT_ID`: GCS project ID
- `DW_GCS_BUCKET`: GCS bucket name

### Core Components

**Click CLI (`datawagon/main.py`)**:
- Entry point with command group using `chain=True` for command chaining
- Loads `.env` file and validates `source_config.toml` against `SourceConfig` model
- Creates `AppConfig` and `SourceConfig` objects, stores in `ctx.obj`

**File Scanner (`datawagon/objects/managed_file_scanner.py`)**:
- `ManagedFileScanner.matched_files()`: Scans source directory for files matching config
- Extracts metadata from filenames using regex patterns
- Returns `List[ManagedFilesToDatabase]` grouping files by destination

**File Metadata (`datawagon/objects/managed_file_metadata.py`)**:
- `ManagedFileMetadata`: Pydantic model storing file info
- Auto-converts `file_date_key` (YYYYMMDD or YYYYMM) to `report_date_str` (YYYY-MM-DD)
- Includes `content_owner`, `file_version`, `base_name`, `storage_folder_name`

**GCS Manager (`datawagon/bucket/gcs_manager.py`)**:
- Wraps Google Cloud Storage client
- `list_blobs()`: Lists files in bucket matching glob pattern
- `upload_blob()`: Uploads file to GCS with destination path
- `files_in_blobs_df()`: Returns DataFrame of files in bucket by base_name

**Commands (`datawagon/commands/`)**:
- `files_in_local_fs`: Scans local directory, validates files, checks for duplicates
- `files_in_storage`: Lists files currently in GCS bucket
- `compare_local_files_to_bucket`: Shows diff between local and bucket files
- `upload_to_storage`: Prompts user and uploads new files with partitioning
- `file_zip_to_gzip`: Converts .zip to .gzip format

### Data Flow

1. CLI loads config from `.env` and validates `source_config.toml`
2. `ManagedFileScanner.matched_files()` scans source directory using config rules
3. For each file, regex extracts metadata (content_owner, file_date_key, etc.)
4. `ManagedFileMetadata` converts extracted data, creates `report_date_str`
5. Commands compare local files to GCS bucket contents
6. Upload creates partitioned path: `{storage_folder_name}/report_date={YYYY-MM-DD}/{filename}`
7. GCS Manager uploads files to bucket

### File Processing

**Supported extensions**: `.csv`, `.csv.gz`, `.csv.zip`

**File name patterns**: Configured per file type. Example:
- Pattern: `YouTube_(.+)_M_(\d{8}|\d{6})`
- Groups: `["content_owner", "file_date_key"]`
- Matches: `YouTube_BrandName_M_20230601_claim_raw_v1-1.csv.gz`
- Extracts: `content_owner="BrandName"`, `file_date_key="20230601"`

**Special handling**:
- `file_date_key` group auto-converts to `report_date_str` for partitioning
- Files starting with `.~lock` are excluded
- Duplicate detection by file name

### Pydantic Models

**Configuration Models** (`datawagon/objects/source_config.py`):
- `SourceConfig`: Root config with `file: dict[str, SourceFromLocalFS]`
- `SourceFromLocalFS`: Per-file-type settings

**Data Models**:
- `AppConfig`: Runtime config (paths, GCS project/bucket)
- `ManagedFileInput`: Raw file attributes before validation
- `ManagedFileMetadata`: Validated file metadata with computed fields
- `ManagedFiles`: Base class grouping files by selector
- `ManagedFilesToDatabase`: Adds table name and append/replace strategy

## Code Style

- Pre-commit hook runs `make pre-commit` (type, isort, format, lint, test)
- Type hints required (checked with mypy)
- Import sorting with isort
- Code formatting with black
- Linting with flake8 (config in `.flake8`)

## Dead Code Detection

DataWagon uses vulture to detect unused code. This is an optional check that helps identify:
- Unused functions, classes, and variables
- Unreachable code
- Redundant imports

### Running Vulture

```bash
make vulture  # Scan datawagon/ directory for dead code
```

### Configuration

- **Confidence threshold:** 70 (medium)
- **Scanned paths:** `datawagon/` only (tests excluded)
- **CI/CD mode:** Advisory (warnings only, doesn't fail builds)

### Interpreting Results

Vulture reports findings with confidence levels (0-100%):
- **80-100%:** Likely dead code - investigate for removal
- **60-79%:** Possibly dead code - review usage patterns
- **Below 60%:** Often false positives from framework code

### Common False Positives

- Click command functions (called dynamically by CLI)
- Pydantic validators (invoked by model validation)
- Entry point functions in `__main__.py`
- Functions exported via `__all__`

If you encounter frequent false positives for specific patterns, create a `vulture_whitelist.py` file to suppress them.

## Migration Guide: Switching Installation Methods

### From Poetry to Standard venv

If you only need to run DataWagon (not develop):

```bash
rm -rf .venv
./setup-venv.sh
source .venv/bin/activate
make verify-install
```

**Trade-offs:**
- Lose: Dev tools, dependency modification
- Gain: 60% faster install, 60% less disk space

### From Standard venv to Poetry

For development/contributions:

```bash
curl -sSL https://install.python-poetry.org | python3 -
rm -rf .venv
make setup-poetry
make test
```

**What you gain:**
- Full development tooling
- Dependency management
- Pre-commit hooks

### Clean Migration Checklist

1. Deactivate: `deactivate`
2. Remove: `rm -rf .venv`
3. Setup: `./setup-venv.sh` or `make setup-poetry`
4. Activate: `source .venv/bin/activate`
5. Verify: `make verify-install`
6. Check: `.env` still configured
7. Test: Run typical commands

## Dependency Management

DataWagon supports both Poetry and pip-based dependency management:

### For Poetry Users (Development)

```bash
poetry add pandas              # Add runtime
poetry add --group dev mypy    # Add dev
poetry lock                    # Update lock
make requirements              # Export
```

### For Non-Poetry Users (Runtime Only)

```bash
pip install -e . --upgrade     # Update DataWagon
```

**Cannot modify dependencies.** To request changes:
1. Open GitHub issue with justification
2. Poetry user updates pyproject.toml
3. Pull changes: `./update-venv.sh`

**Why:** Ensures dependency consistency and maintains poetry.lock as single source of truth.

### Requirements File Structure

- **requirements.txt** (41 packages): Runtime only
  - click, pandas, pydantic, google-cloud-storage
  - Used by: Standard venv, Docker, CI/CD

- **requirements-dev.txt** (106 packages): Runtime + Dev
  - All runtime + mypy, black, flake8, pytest
  - Used by: Poetry install, contributors

**Both auto-generated - do not edit manually.**

### Keeping Requirements in Sync (Poetry Users Only)

```bash
make requirements         # Generates requirements.txt and requirements-dev.txt
```

Pre-commit hooks automatically check that requirements files are in sync (Poetry users only). Non-Poetry users will see a skip message, which is expected and normal.
