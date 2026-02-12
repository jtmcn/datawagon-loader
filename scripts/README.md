# DataWagon Scripts

Utility scripts for DataWagon maintenance and operations.

## cleanup_old_naming.py

Removes GCS folders and BigQuery tables created with the old naming convention (without version suffixes).

### Problem

Before version 1.2.0, DataWagon created folders without version suffixes:
- ❌ Old: `caravan-versioned/claim_raw/`
- ✅ New: `caravan-versioned/claim_raw_v1-1/`

This script cleans up the old folders and associated BigQuery tables.

### Prerequisites

1. **Environment variables** set in `.env`:
   ```bash
   DW_GCS_PROJECT_ID=your-project-id
   DW_GCS_BUCKET=your-bucket-name
   DW_BQ_DATASET=your-dataset-name
   ```

2. **Google Cloud authentication** configured:
   ```bash
   gcloud auth application-default login
   ```

3. **Python dependencies** installed:
   ```bash
   pip install google-cloud-storage google-cloud-bigquery python-dotenv rich
   ```

### Usage

#### Using the Wrapper Script (Recommended)

The easiest way to run the cleanup:

```bash
# Dry run (safe - shows what would be deleted)
./scripts/cleanup.sh --dry-run

# Delete with confirmation
./scripts/cleanup.sh

# Force delete (skip confirmation)
./scripts/cleanup.sh --force
```

The wrapper script:
- Activates your `.venv` automatically
- Loads environment variables from `.env`
- Passes all arguments to the cleanup script

#### Direct Python Usage

If you prefer to run the Python script directly:

```bash
# Activate virtual environment
source .venv/bin/activate

# Dry run
python scripts/cleanup_old_naming.py --dry-run

# Delete with confirmation
python scripts/cleanup_old_naming.py

# Force delete
python scripts/cleanup_old_naming.py --force
```

#### Custom Storage Prefix

```bash
./scripts/cleanup.sh --dry-run --storage-prefix my-custom-prefix
# Or directly:
python scripts/cleanup_old_naming.py --dry-run --storage-prefix my-custom-prefix
```

Use if you changed the default `caravan-versioned` prefix.

### Example Output

```
DataWagon Old Naming Cleanup

Project ID: my-project
Bucket: my-bucket
Dataset: youtube_analytics
Storage Prefix: caravan-versioned

Scanning for folders without version suffixes...
Finding BigQuery tables pointing to old folders...

═══ Cleanup Summary ═══

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ GCS Folders to Delete           ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ caravan-versioned/claim_raw     │
│ caravan-versioned/ownership_raw │
└─────────────────────────────────┘

┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Table Name    ┃ Source URI                        ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ claim_raw     │ gs://bucket/caravan-versioned/... │
│ ownership_raw │ gs://bucket/caravan-versioned/... │
└───────────────┴───────────────────────────────────┘

Total folders to delete: 2
Total tables to drop: 2

This is a DRY RUN - nothing will be deleted
```

### Safety Features

1. **Dry run by default**: Use `--dry-run` to preview changes
2. **Confirmation required**: Type `DELETE` to confirm (unless `--force`)
3. **Tables dropped first**: Removes table references before deleting data
4. **Detailed logging**: Shows every file and table being processed
5. **Pattern matching**: Only deletes folders WITHOUT version suffixes

### What Gets Identified

The script finds folders that:
- Are under the storage prefix (e.g., `caravan-versioned/`)
- Do NOT end with a version suffix pattern `_vX-Y` (e.g., `_v1-1`)

It preserves folders that:
- Have version suffixes (e.g., `claim_raw_v1-1/`)
- Are outside the storage prefix

### After Cleanup

Once old resources are deleted:

1. **Re-upload files** with the new version:
   ```bash
   datawagon compare-local-to-bucket upload-to-gcs
   ```

2. **Create new tables**:
   ```bash
   datawagon create-bigquery-tables
   ```

3. **Verify setup**:
   ```bash
   datawagon list-bigquery-tables
   datawagon files-in-storage
   ```

### Troubleshooting

**Error: Missing environment variables**
- Check that `.env` file exists in project root
- Ensure `DW_GCS_PROJECT_ID`, `DW_GCS_BUCKET`, `DW_BQ_DATASET` are set

**Error: Could not authenticate**
- Run: `gcloud auth application-default login`
- Or set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

**Script finds nothing to delete**
- Good news! Your bucket is already using the new naming convention
- Or you're using a different storage prefix (use `--storage-prefix` flag)

**Want to test on a subset**
- Copy one folder to a test bucket
- Run script against test bucket by changing `.env` temporarily

### Recovery

If you accidentally delete the wrong folders:

1. **Stop immediately** (Ctrl+C)
2. **Check GCS bucket versioning** (if enabled, you can recover)
3. **Re-upload from local source** using `datawagon upload-to-gcs`

### Source Code

The script uses:
- `google.cloud.storage` to list and delete GCS blobs
- `google.cloud.bigquery` to drop external tables
- `rich` for formatted output
- Regex pattern `_v\d+-\d+$` to identify version suffixes
