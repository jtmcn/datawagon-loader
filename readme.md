# DataWagon Loader

Automated ingestion and upload of YouTube Analytics CSV files to Google Cloud Storage

### Background
This project was built to replace an existing process which used a bash file to load uncompressed files into a Postgres instance. The original script was not able to handle compressed files, and required manually moving files in and out of an import directory. It had no mechanism to check for duplicate files, and no way to check if files had already been processed.

### Goals
1. Leave existing process relatively intact. The user will still download the csv files and place them in a directory
2. Use the existing file storage and remove necessity of moving files in and out of an import directory
3. Allow for compressed files
4. Check for duplicate files
5. Prevent files from being uploaded more than once
6. Provide user feedback on the status of the upload process
7. Extract metadata from filenames and organize files in cloud storage 


### Pipeline Setup

#### Install Application
Open `Terminal.app`
Retrieve code from GitHub
```
git clone https://github.com/jtmcn/datawagon.git
```
Move into loader folder
```
cd datawagon/loader
```
Setup environment
```
./update.sh
```

#### Configuration

##### Environment Variables
Four runtime variables are required. They may be passed in as parameters or as environment variables. An easy way to manage them is by putting them in a `.env` file in the loader directory.

Required Variables:
- `DW_CSV_SOURCE_DIR` - Directory containing YouTube Analytics CSV files
- `DW_CSV_SOURCE_TOML` - Path to datawagon-config.toml file
- `DW_GCS_PROJECT_ID` - Google Cloud Storage project ID
- `DW_GCS_BUCKET` - Google Cloud Storage bucket name

Example `.env` file:
```
DW_CSV_SOURCE_DIR=/path/to/youtube/csv/files
DW_CSV_SOURCE_TOML=/path/to/datawagon-config.toml
DW_GCS_PROJECT_ID=your-gcp-project-id
DW_GCS_BUCKET=your-gcs-bucket-name
```

##### Configuration File
The `datawagon-config.toml` file defines how different file types should be processed. Each file type configuration includes:
- `storage_folder_name` - Destination folder in GCS
- `regex_pattern` - Pattern to extract metadata from filenames
- `regex_group_names` - Names for extracted metadata (e.g., content_owner, file_date_key)
- `select_file_name_base` - File name pattern to match
- `exclude_file_name_base` - File name pattern to exclude

#### Google Cloud Authentication

DataWagon uses Google Application Default Credentials (ADC) for authentication. No explicit credentials need to be configured in the application.

##### Local Development
Choose one of these authentication methods:

**Option 1: gcloud CLI (Recommended)**
```bash
# Login with your Google account
gcloud auth application-default login
```

**Option 2: Service Account Key File**
```bash
# Set environment variable to point to your service account JSON file
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

##### Production Environments
- **Google Kubernetes Engine (GKE)**: Use Workload Identity Federation
- **Google Compute Engine (GCE)**: Use attached service accounts
- **Other environments**: Use service account key files (least preferred)

##### Troubleshooting Authentication
If you encounter authentication errors, the application will display:
```
Error connecting to GCS: [error details]
Make sure you're logged-in: gcloud auth application-default login
```

Common issues:
- Not authenticated: Run `gcloud auth application-default login`
- Wrong project: Check your gcloud configuration with `gcloud config list`
- Missing permissions: Ensure your account has Storage Object Admin role on the bucket



### Usage

#### Available Commands

```bash
# Activate the environment
cd ~/Code/datawagon/loader
source .venv/bin/activate

# List files in local filesystem
datawagon files-in-local-fs

# List files already in GCS bucket
datawagon files-in-storage

# Compare local files to bucket (see what's new)
datawagon compare-local-files-to-bucket

# Upload new files to GCS
datawagon upload-to-gcs

# Convert zip files to gzip format
datawagon file-zip-to-gzip
```

#### Typical Workflow
When new files have been added to the source folder and should be uploaded to GCS:

```bash
cd ~/Code/datawagon/loader
./update.sh # optional - updates code and dependencies
source .venv/bin/activate

# Compare and upload in one command chain
datawagon compare-local-files-to-bucket upload-to-gcs
```

This will:
1. Scan files in `DW_CSV_SOURCE_DIR` based on patterns in config
2. Check which files already exist in the GCS bucket
3. Display a comparison table showing new files
4. Prompt for confirmation before uploading
5. Upload files with proper folder structure and partitioning

#### Data Organization in GCS

Files are organized in GCS with the following structure:
```
bucket/
├── caravan/
│   ├── claim_raw/
│   │   └── report_date=20230601/
│   │       └── YouTube_BrandName_M_20230601_claim_raw_v1-1.csv.gz
│   ├── asset_raw/
│   │   └── report_date=20230601/
│   │       └── YouTube_BrandName_M_20230601_asset_raw_v1.csv.gz
│   └── video_raw/
│       └── report_date=20230601/
│           └── YouTube_BrandName_M_20230601_video_raw_v1.csv.gz
```

The loader automatically:
- Extracts metadata from filenames using regex patterns
- Creates partitioned folders by report_date
- Preserves original filenames
- Adds metadata columns when processing

### Usage Notes
- Supported file extensions: `.csv`, `.csv.gz`, `.csv.zip`, `.tar.gz`
- Files are matched based on patterns defined in `datawagon-config.toml`
- The loader extracts metadata like content_owner and report_date from filenames
- Files are partitioned by report_date in GCS for efficient querying
- Duplicate files are detected and prevented from re-uploading
