# DataWagon

[![Build Status](https://github.com/joeltkeller/datawagon/workflows/Build/badge.svg)](https://github.com/joeltkeller/datawagon/actions/workflows/build.yml)
[![Release](https://github.com/joeltkeller/datawagon/workflows/Release/badge.svg)](https://github.com/joeltkeller/datawagon/actions/workflows/release.yml)
[![codecov](https://codecov.io/gh/joeltkeller/datawagon/branch/main/graph/badge.svg)](https://codecov.io/gh/joeltkeller/datawagon)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Automated loading of YouTube Analytics CSV files into Google Cloud Storage buckets with BigQuery external table management.

## Overview

DataWagon processes compressed YouTube Analytics files (.csv.gz, .csv.zip), validates filenames against regex patterns, extracts metadata, and uploads them to Google Cloud Storage with automatic partitioning by report date. It also manages BigQuery external tables that reference the uploaded files, enabling direct SQL queries without data duplication.

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
8. **BigQuery external table management** - create and list tables that reference GCS files
9. Automatic schema detection from CSV headers
10. Hive partitioning support for efficient date-based queries
11. Comprehensive validation and user feedback

---

## Prerequisites

- Python 3.9 or higher (3.12 recommended)
- Google Cloud Platform account with Storage and BigQuery access
- Google Cloud credentials configured locally

**Optional:**
- [Poetry](https://python-poetry.org/) 2.0 or higher (for dependency management)

---

## First-Time Setup

### Option 1: Quick Setup (Without Poetry)

For users who want to use DataWagon without Poetry:

```bash
git clone https://github.com/jtmcn/datawagon.git
cd datawagon
./setup-venv.sh
source .venv/bin/activate
datawagon --help
```

This creates a standard Python virtual environment and installs DataWagon from source.

### Option 2: Development Setup (With Poetry)

Poetry is recommended if you plan to modify dependencies or contribute to development.

#### 1. Clone Repository

```bash
git clone https://github.com/jtmcn/datawagon.git
cd datawagon
```

#### 2. Install Poetry

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

#### 3. Run Setup

```bash
make setup-poetry
```

This will:
- Check Poetry installation
- Install required Poetry plugins (poetry-plugin-export)
- Create `.env` from `.env.example`
- Install all dependencies
- Create virtual environment in `.venv/`

### Installation Methods Compared

| Feature | Poetry (Development) | Standard venv (Runtime) |
|---------|---------------------|------------------------|
| Install DataWagon | ✓ | ✓ |
| Run commands | ✓ | ✓ |
| Modify application code | ✓ | ✓ |
| Development tools (mypy, black, flake8, pytest) | ✓ | ✗ |
| Add/modify dependencies | ✓ | Request via issue |
| Lock dependencies | ✓ | Use requirements.txt |
| Installation time | ~2 min | ~30 sec |
| Disk space | ~500MB | ~200MB |
| Use case | Development, contributions | Running the app only |

**Recommendation:**
- Use **standard venv** if you just want to use DataWagon (simpler, faster, smaller)
- Use **Poetry** if you're developing, contributing, or managing dependencies

### Configuration (Both Options)

Edit `.env` with your settings:

```bash
# Local CSV source directory
DW_CSV_SOURCE_DIR=/path/to/your/csv/files

# Source configuration (keep default unless customizing)
DW_CSV_SOURCE_TOML=./datawagon-config.toml

# Google Cloud Storage settings
DW_GCS_PROJECT_ID=your-gcp-project-id
DW_GCS_BUCKET=your-bucket-name

# BigQuery settings
DW_BQ_DATASET=your_dataset_name
DW_BQ_STORAGE_PREFIX=caravan-versioned  # Optional: filter which folders to scan (default: caravan-versioned)
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

### With Poetry

To pull latest changes and update dependencies:

```bash
./update.sh
```

### Without Poetry (Standard venv)

To pull latest changes and update dependencies:

```bash
./update-venv.sh
```

Or manually:

```bash
git pull
source .venv/bin/activate
pip install -e . --upgrade
```

### Switching Installation Methods

#### From Poetry to Standard venv

```bash
rm -rf .venv
./setup-venv.sh
source .venv/bin/activate
datawagon --help
```

**What changes:**
- Smaller: ~200MB vs ~500MB
- No dev tools (mypy, black, flake8, pytest)
- Faster setup: ~30 sec vs ~2 min
- Cannot modify dependencies

#### From Standard venv to Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
rm -rf .venv
make setup-poetry
source .venv/bin/activate
make test
```

**What you gain:**
- Full development tooling
- Ability to modify dependencies
- Run pre-commit checks locally

#### Verifying Installation Type

```bash
make verify-install  # Shows installation type
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

**File Management:**
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

**BigQuery External Tables:**
```bash
# List existing external tables in BigQuery dataset
datawagon list-bigquery-tables

# Create external tables for GCS folders without tables
datawagon create-bigquery-tables

# Drop external tables (dry-run by default)
datawagon drop-bigquery-tables

# Actually execute deletion (requires confirmation)
datawagon drop-bigquery-tables --execute
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
TO:   caravan-versioned/claim_raw_v1-1/report_date=2025-07-31/YouTube_Brand_M_20250701_claim_raw_v1-1.csv.gz
```

Note: The migration changes the root folder from `caravan` to `caravan-versioned` and adds version suffixes.

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

### BigQuery External Tables

After uploading files to GCS, you can create BigQuery external tables that reference the files directly. This allows you to query the CSV data using SQL without loading it into BigQuery storage.

**List existing tables:**

```bash
datawagon list-bigquery-tables
```

This displays:
- Table names (with version suffixes, e.g., `claim_raw_v1_1`)
- Creation timestamps
- Partitioning status
- Source URI patterns

**Create missing tables:**

```bash
datawagon create-bigquery-tables
```

This will:
1. Scan GCS bucket for folders under the configured prefix (default: `caravan-versioned`)
2. List existing BigQuery external tables
3. Identify folders without corresponding tables
4. Show a summary of tables to be created
5. Prompt for confirmation
6. Create external tables with:
   - Auto-detected schema from CSV headers
   - Hive partitioning on `report_date` column (for partitioned folders)
   - GZIP compression support
   - CSV format configuration

**Example table creation:**

```
Storage folder: caravan-versioned/claim_raw_v1-1
→ BigQuery table: claim_raw_v1_1
→ Source URI: gs://bucket/caravan-versioned/claim_raw_v1-1/*
→ Partitioning: Yes (report_date)
```

**Querying external tables:**

Once created, query the tables in BigQuery:

```sql
-- Query with partition filtering for efficiency
SELECT * FROM `project.dataset.claim_raw_v1_1`
WHERE report_date = '2023-06-30'
LIMIT 10;

-- Aggregate across all partitions
SELECT report_date, COUNT(*) as claim_count
FROM `project.dataset.claim_raw_v1_1`
GROUP BY report_date
ORDER BY report_date DESC;
```

**Key benefits:**
- No data duplication (files stay in GCS, BigQuery reads directly)
- Automatic schema detection (no manual schema definition)
- Partition pruning for fast date-filtered queries
- Multiple versions can coexist as separate tables

**Configuration:**

Control which folders are scanned with the `DW_BQ_STORAGE_PREFIX` setting:

```bash
# Only scan caravan-versioned folders (default)
DW_BQ_STORAGE_PREFIX=caravan-versioned

# Scan all folders (legacy behavior)
DW_BQ_STORAGE_PREFIX=""

# Scan a different prefix
DW_BQ_STORAGE_PREFIX=my-custom-folder
```

**Drop tables:**

```bash
# Dry-run: Show what would be deleted (safe, default)
datawagon drop-bigquery-tables

# Drop all tables in dataset (requires confirmation)
datawagon drop-bigquery-tables --execute

# Drop specific table
datawagon drop-bigquery-tables --execute --table-name claim_raw_v1_1

# Drop from specific dataset
datawagon drop-bigquery-tables --execute --dataset my_dataset
```

This command:
- Defaults to dry-run mode (safe preview)
- Requires `--execute` flag to actually delete
- Shows all tables to be dropped before deletion
- Requires explicit user confirmation
- Only deletes table metadata (CSV files in GCS remain untouched)
- Provides detailed progress and error reporting

**Safety features:**
- Dry-run mode by default prevents accidental deletions
- User must explicitly confirm before any deletion
- Individual table errors don't stop batch operations
- Comprehensive logging for audit trail

### Chaining Commands

Commands can be chained together:

```bash
datawagon files-in-local-fs compare-local-to-bucket upload-to-gcs
```

### Typical Workflow

**When you have new files to upload:**

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

**Complete workflow with BigQuery table creation:**

```bash
datawagon upload-to-gcs create-bigquery-tables
```

This uploads new files and automatically creates any missing BigQuery external tables in one command chain.

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
gs://my-bucket/caravan-versioned/some_file/report_date=2024-01-15/file.csv.gz

# Versioned file (version automatically extracted from filename)
gs://my-bucket/caravan-versioned/claim_raw_v1-1/report_date=2024-01-15/YouTube_BrandName_M_20240115_claim_raw_v1-1.csv.gz
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
│   │   ├── migrate_to_versioned_folders.py
│   │   ├── list_bigquery_tables.py
│   │   └── create_bigquery_tables.py
│   ├── objects/                 # Core data models
│   │   ├── app_config.py
│   │   ├── source_config.py
│   │   ├── managed_file_metadata.py
│   │   ├── managed_file_scanner.py
│   │   └── bigquery_table_metadata.py
│   └── bucket/                  # GCS and BigQuery integration
│       ├── gcs_manager.py
│       └── bigquery_manager.py
├── tests/                       # Test suite
│   ├── test_bigquery_manager.py
│   ├── test_bigquery_table_metadata.py
│   ├── test_create_bigquery_tables.py
│   └── ...
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

### Command not found after setup

If `datawagon` command is not found after running setup:

```bash
# Verify virtual environment activation
which python  # Should show /path/to/datawagon/.venv/bin/python

# If not in venv, activate it
source .venv/bin/activate

# Verify installation
datawagon --help
```

If still not working:
```bash
# Reinstall from scratch
rm -rf .venv
./setup-venv.sh
source .venv/bin/activate
```

### Why don't I have pytest/mypy/black?

These are development tools, not included in standard venv installation (runtime-only).

**If you need development tools**, use Poetry:
```bash
rm -rf .venv
make setup-poetry
```

**If you just want to run tests occasionally**, install manually:
```bash
source .venv/bin/activate
pip install pytest mypy black flake8
```

### Can I develop without Poetry?

Yes, but it's not recommended:
- **Code changes**: Edit files normally in either installation
- **Run application**: Works the same in both
- **Run tests**: Manually install dev dependencies (see above)
- **Modify dependencies**: Not possible - must request via GitHub issue

For serious development or contributions, Poetry is strongly recommended.

### How do I know which installation I have?

```bash
make verify-install
```

This will show:
- Installation type (Poetry vs Standard venv)
- Virtual environment location
- Whether installation is healthy

### Python version mismatch

**Symptom**: `setup-venv.sh` fails with "Python 3.9+ required".

**Solution**:
```bash
# Check your Python version
python3 --version

# If Python 3.8 or earlier, upgrade Python first
# On macOS with Homebrew:
brew install python@3.11

# On Ubuntu/Debian:
sudo apt update
sudo apt install python3.11

# Verify new version
python3.11 --version

# Create venv with specific Python version
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**Common causes**:
- System Python is outdated
- Multiple Python versions installed (using wrong one)
- Virtual environment created with old Python

### pip installation fails with "externally-managed-environment"

**Symptom**: `pip install` fails with:
```
error: externally-managed-environment
```

**Solution**: This is expected on some modern Linux distros (Debian 12+, Ubuntu 23.04+). The virtual environment approach handles this:

```bash
# Virtual environment bypasses external management
python3 -m venv .venv
source .venv/bin/activate
pip install -e .  # Now works inside venv
```

**Don't**: Never use `pip --break-system-packages` - this is dangerous.

### Shell script fails with "command not found: poetry"

**Symptom**: `update.sh` fails because Poetry not found.

**This is expected**:
- `update.sh` is for Poetry users only
- For non-Poetry users, use `update-venv.sh` instead

**Solution**:
```bash
# Non-Poetry users:
./update-venv.sh

# Poetry users - install Poetry first:
curl -sSL https://install.python-poetry.org | python3 -
```

### Installation succeeds but datawagon command not found

**Symptom**: After `./setup-venv.sh` completes, `datawagon` command not found.

**Cause**: Virtual environment not activated.

**Solution**:
```bash
# Activate virtual environment
source .venv/bin/activate

# Verify activation (should show .venv path)
which python

# Now datawagon should work
datawagon --help
```

**To avoid**: Add activation to your shell profile:
```bash
# Add to ~/.bashrc or ~/.zshrc
alias dw='cd /path/to/datawagon && source .venv/bin/activate'
```

### setup-venv.sh hangs on "Installing dependencies"

**Symptom**: Script appears frozen during `pip install -e .`.

**This is usually normal**: First installation downloads ~100MB of packages. Can take 2-5 minutes on slow connections.

**To monitor progress**:
```bash
# Run with verbose output
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e . -v  # Verbose mode shows progress
```

**If truly stuck** (>10 minutes):
```bash
# Ctrl+C to cancel
# Check disk space
df -h .

# Check network
curl -I https://pypi.org/simple/

# Try with timeout
pip install -e . --timeout 60
```

### Requirements file has merge conflict

**Symptom**: After git merge, `requirements.txt` has conflict markers:
```
<<<<<<< HEAD
package==1.0.0
=======
package==2.0.0
>>>>>>> branch
```

**Solution**: Never manually edit requirements files. Regenerate from poetry.lock:

```bash
# Don't manually resolve conflict
# Instead, resolve poetry.lock conflict first

git checkout --theirs poetry.lock  # Or --ours, depending on which you want

# Then regenerate requirements
make requirements

# Stage the regenerated files
git add requirements.txt requirements-dev.txt poetry.lock
```

### Tests pass locally but fail in CI

**Symptom**: `make test` passes locally, but GitHub Actions fails.

**Common causes**:
1. **Missing dependency in poetry.lock**: CI installs from lock file only
   ```bash
   # Add missing dependency
   poetry add missing-package
   poetry lock
   make requirements
   git add pyproject.toml poetry.lock requirements*.txt
   git commit
   ```

2. **Local vs CI Python version**: CI tests on 3.9, 3.10, 3.11
   ```bash
   # Test with specific Python version locally (requires pyenv)
   pyenv install 3.9.18
   pyenv local 3.9.18
   rm -rf .venv
   make setup
   make test
   ```

3. **Environment variable differences**: CI doesn't have your local `.env`
   ```bash
   # Check which env vars your code uses
   grep -r "os.environ" datawagon/

   # Ensure tests mock external dependencies
   # (GCS, BigQuery, etc.)
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

### BigQuery dataset not found

Create the dataset before running BigQuery commands:

```bash
bq mk --dataset your-project-id:your_dataset_name
```

### BigQuery authentication errors

Ensure you have BigQuery permissions:

```bash
# Authenticate with GCP
gcloud auth application-default login

# Verify you have BigQuery access
bq ls --project_id=your-project-id
```

Required IAM roles:
- `roles/bigquery.dataEditor` - Create and manage tables
- `roles/storage.objectViewer` - Read CSV files from GCS

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run `make pre-commit` to verify quality
5. Commit changes
6. Push and create pull request

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes and version releases.

---

## License

MIT License - see LICENSE file for details

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/jtmcn/datawagon/issues
- Email: jtmcn.dev@gmail.com
