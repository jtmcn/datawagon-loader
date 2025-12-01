# DataWagon

Automated loading of YouTube Analytics CSV files into Google Cloud Storage buckets.

## Overview

DataWagon processes compressed YouTube Analytics files (.csv.gz, .csv.zip), validates filenames against regex patterns, extracts metadata, and uploads them to Google Cloud Storage with automatic partitioning by report date.

### Background

This project was built to replace an existing process which used a bash script to load uncompressed files into a PostgreSQL database. The original script could not handle compressed files, required manually moving files in and out of an import directory, had no mechanism to check for duplicate files, and required code modification and manual table creation to add new types of files.

### Key Features

1. Automatic compressed file handling (.csv.gz, .csv.zip)
2. Duplicate file detection and prevention
3. Configurable file type patterns via TOML configuration
4. GCS bucket integration with automatic partitioning
5. Metadata extraction from filenames using regex
6. Version-based folder organization for BigQuery external table mapping
7. Migration tools for reorganizing existing files into versioned folders
8. Comprehensive validation and user feedback

---

## Prerequisites

- Python 3.9 or higher (3.12 recommended)
- [Poetry](https://python-poetry.org/) 2.0 or higher
- Google Cloud Platform account with Storage access
- Google Cloud credentials configured locally

---

## First-Time Setup

### 1. Clone Repository

```bash
git clone https://github.com/jtmcn/datawagon.git
cd datawagon
```

### 2. Install Poetry

If you don't have Poetry installed:

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Or via pipx
pipx install poetry
```

Verify installation:
```bash
poetry --version
```

### 3. Run Setup

```bash
make setup
```

This will:
- Check Poetry installation
- Install required Poetry plugins (poetry-plugin-export)
- Create `.env` from `.env.example`
- Install all dependencies
- Create virtual environment in `.venv/`

### 4. Configure Environment

Edit `.env` with your settings:

```bash
# Local CSV source directory
DW_CSV_SOURCE_DIR=/path/to/your/csv/files

# Source configuration (keep default unless customizing)
DW_CSV_SOURCE_TOML=./datawagon-config.toml

# Google Cloud Storage settings
DW_GCS_PROJECT_ID=your-gcp-project-id
DW_GCS_BUCKET=your-bucket-name
```

### 5. Configure Google Cloud Credentials

```bash
# Authenticate with GCP
gcloud auth application-default login

# Or set service account key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### 6. Verify Installation

```bash
source .venv/bin/activate
datawagon --help
```

---

## Updating Existing Installation

To pull latest changes and update dependencies:

```bash
./update.sh
```

Or manually:

```bash
git pull
poetry install
make requirements
```

---

## Usage

### Activate Virtual Environment

```bash
source .venv/bin/activate
```

Or run commands via Poetry:

```bash
poetry run datawagon --help
```

### Available Commands

```bash
# List files in local source directory
datawagon files-in-local-fs

# List files already in GCS bucket
datawagon files-in-storage

# Compare local files to bucket
datawagon compare-local-to-bucket

# Upload new files to GCS
datawagon upload-to-gcs

# Convert .zip files to .gzip format
datawagon file-zip-to-gzip

# Migrate existing files to versioned folder structure
datawagon migrate-to-versioned-folders
```

### Migrating to Versioned Folders

If you have existing files in GCS that need to be reorganized into version-specific folders (e.g., moving files from `caravan/claim_raw/` to `caravan/claim_raw_v1-1/`), use the migration command.

**When to use this:**
- You have versioned files (containing `_v1-0`, `_v1-1`, etc. in filenames) in non-versioned folders
- You want to organize different file versions into separate folders for BigQuery external table mapping
- You need stable folder paths for each version to maintain BigQuery table continuity

**Dry-run (default - safe to run):**

```bash
datawagon migrate-to-versioned-folders
```

This will:
1. Scan your GCS bucket for all files
2. Extract version information from filenames
3. Show a detailed migration plan grouped by file type
4. Display what would be migrated without making any changes

**Execute migration:**

```bash
datawagon migrate-to-versioned-folders --execute
```

This will:
1. Show the migration plan
2. Prompt for confirmation
3. Copy files to versioned folders with progress tracking
4. Preserve original files (you can delete them manually after verification)
5. Display summary and next steps

**Example transformation:**

```
FROM: caravan/claim_raw/report_date=2025-07-31/YouTube_Brand_M_20250701_claim_raw_v1-1.csv.gz
TO:   caravan/claim_raw_v1-1/report_date=2025-07-31/YouTube_Brand_M_20250701_claim_raw_v1-1.csv.gz
```

**Post-migration workflow:**

1. Verify files copied correctly: `datawagon files-in-storage`
2. Update BigQuery external table URIs to point to versioned folders
3. Test BigQuery queries against new table locations
4. Once verified, delete original files from GCS (via console or `gsutil`)

**Safety features:**
- Dry-run mode by default (must explicitly use `--execute`)
- User confirmation required before copying
- Original files never deleted
- Each copy is verified before marking success
- Individual file errors don't stop the migration

### Chaining Commands

Commands can be chained together:

```bash
datawagon files-in-local-fs compare-local-to-bucket upload-to-gcs
```

### Typical Workflow

When you have new files to upload:

```bash
cd ~/Code/datawagon
source .venv/bin/activate
datawagon files-in-local-fs compare-local-to-bucket upload-to-gcs
```

This will:
1. Scan local directory for valid CSV files
2. Check for duplicates and invalid filenames
3. Compare with files already in GCS bucket
4. Show summary of new files to upload
5. Prompt for confirmation
6. Upload files with partitioning by report date

---

## Configuration

### File Type Configuration

Edit `datawagon-config.toml` to define file types and patterns:

```toml
[file.youtube_claims]
select_file_name_base = "YouTube_*_claim_*"
exclude_file_name_base = "YouTube_*_claim_historical_*"
regex_pattern = "YouTube_(.+)_M_(\\d{8}|\\d{6})"
regex_group_names = ["content_owner", "file_date_key"]
storage_folder_name = "youtube_claims"
table_name = "claims"
table_append_or_replace = "append"
```

**Configuration Fields:**
- `select_file_name_base`: Glob pattern to match files
- `exclude_file_name_base`: Glob pattern to exclude files
- `regex_pattern`: Regex to extract metadata from filename
- `regex_group_names`: Named groups from regex (e.g., `["content_owner", "file_date_key"]`)
- `storage_folder_name`: GCS destination folder
- `table_name`: Table identifier for tracking
- `table_append_or_replace`: Upload strategy (append or replace)

### Special Metadata Fields

- `file_date_key`: Auto-converts YYYYMMDD or YYYYMM to YYYY-MM-DD format for partitioning
- `content_owner`: Typically extracted from filename for organization

### GCS Upload Structure

Files are uploaded with this structure:

```
gs://your-bucket/storage_folder_name/report_date=YYYY-MM-DD/filename.csv.gz
```

**For versioned files**, the version is automatically appended to the folder name:

```
gs://your-bucket/storage_folder_name_v1-1/report_date=YYYY-MM-DD/filename.csv.gz
```

Examples:
```
# Non-versioned file
gs://my-bucket/youtube_claims/report_date=2024-01-15/YouTube_BrandName_M_20240115_claims.csv.gz

# Versioned file (version automatically extracted from filename)
gs://my-bucket/youtube_claims_v1-1/report_date=2024-01-15/YouTube_BrandName_M_20240115_claims_v1-1.csv.gz
```

This ensures each file version has a stable folder path for BigQuery external table mapping.

---

## Development

### Setup Development Environment

```bash
make setup
source .venv/bin/activate
```

### Code Quality Tools

```bash
make type       # Type check with mypy
make isort      # Sort imports
make format     # Format code with black
make lint       # Lint with flake8
make test       # Run tests with pytest
```

### Run All Checks

```bash
make pre-commit      # Run all quality checks
make pre-commit-fast # Run faster checks (type, lint, test only)
```

### Update Dependencies

```bash
# Update all dependencies
make update

# Add new dependency
poetry add <package-name>

# Add dev dependency
poetry add --group dev <package-name>

# Regenerate requirements.txt
make requirements
```

### Testing

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run specific test
poetry run pytest tests/file_utils_test.py -k test_group_by_base_name
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. They will:
- Run all code quality checks (type, isort, format, lint, test)
- Verify requirements.txt is in sync with poetry.lock

To skip during development:

```bash
git commit --no-verify
```

### Build Distribution

```bash
make build-app
```

Builds wheel and source distribution in `dist/` directory.

---

## Project Structure

```
datawagon/
├── datawagon/
│   ├── __main__.py              # CLI entry point
│   ├── main.py                  # Click CLI setup
│   ├── commands/                # Command implementations
│   │   ├── files_in_local_fs.py
│   │   ├── files_in_storage.py
│   │   ├── compare.py
│   │   ├── upload_to_storage.py
│   │   ├── file_zip_to_gzip.py
│   │   └── migrate_to_versioned_folders.py
│   ├── objects/                 # Core data models
│   │   ├── app_config.py
│   │   ├── source_config.py
│   │   ├── managed_file_metadata.py
│   │   └── managed_file_scanner.py
│   └── bucket/                  # GCS integration
│       └── gcs_manager.py
├── tests/                       # Test suite
├── pyproject.toml               # Poetry configuration
├── poetry.lock                  # Locked dependencies
├── datawagon-config.toml        # File type configuration
├── .env.example                 # Environment template
├── Makefile                     # Development commands
└── update.sh                    # Update script
```

---

## Supported File Extensions

- `.csv` - Uncompressed CSV
- `.csv.gz` - Gzip compressed CSV
- `.csv.zip` - Zip compressed CSV

Files starting with `.~lock` are automatically excluded.

---

## Troubleshooting

### Poetry export command not found

Install the export plugin:

```bash
poetry self add poetry-plugin-export
```

### Virtual environment not found

Recreate the environment:

```bash
rm -rf .venv
make setup
```

### Requirements.txt out of sync

Regenerate from poetry.lock:

```bash
make requirements
```

### Google Cloud authentication errors

Ensure credentials are configured:

```bash
# Option 1: Application default credentials
gcloud auth application-default login

# Option 2: Service account key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### Import errors or missing dependencies

Ensure dependencies are installed:

```bash
poetry install
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run `make pre-commit` to verify quality
5. Commit changes
6. Push and create pull request

---

## License

MIT License - see LICENSE file for details

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/jtmcn/datawagon/issues
- Email: jtmcn.dev@gmail.com
