# DataWagon User Guide for Dave (macOS)

## About This Guide

This guide is for **monthly DataWagon usage on macOS**. It covers:

- One-time setup (upgrading from pre-1.0.0)
- Typical workflow for uploading files and creating BigQuery tables
- Future update process
- Basic troubleshooting

---

## One-Time Setup (Upgrading from Pre-1.0.0)

Follow these steps to upgrade your existing DataWagon installation:

1. **Open Terminal**

2. **Navigate to your DataWagon directory**

   ```bash
   cd /path/to/datawagon
   ```

   Replace `/path/to/datawagon` with your actual path

3. **Pull the latest changes**

   ```bash
   git pull
   ```

4. **Remove the old virtual environment**

   ```bash
   rm -rf .venv
   ```

5. **Run the setup script**

   ```bash
   ./setup-venv.sh
   ```

   This will take about 30 seconds and install all necessary dependencies.

6. **Activate the virtual environment**

   ```bash
   source .venv/bin/activate
   ```

   You should see `(.venv)` appear at the start of your terminal prompt.

7. **Verify the installation**

   ```bash
   datawagon --help
   ```

   You should see a list of available commands.

**Important:** Your existing `.env` file will be preserved automatically. You don't need to reconfigure it.

---

## Monthly Usage

This is your regular workflow for uploading new YouTube Analytics files:

1. **Open Terminal**

2. **Navigate to DataWagon directory**

   ```bash
   cd /path/to/datawagon
   ```

3. **Activate the virtual environment**

   ```bash
   source .venv/bin/activate
   ```

   Look for `(.venv)` at the start of your prompt to confirm it's active.

4. **Run the monthly command**

   ```bash
   datawagon upload-to-gcs create-bigquery-tables
   ```

5. **Respond to the prompts**

   You'll see two prompts:

   **First prompt** (file upload):

   ```
   Upload X new files? [y/N]:
   ```

   Type `y` and press Enter to upload the files.

   **Second prompt** (table creation):

   ```
   Create X BigQuery external tables? [y/N]:
   ```

   Type `y` and press Enter to create the tables.

6. **Review the output**

   Check for any error messages. If everything succeeded, you'll see confirmation messages.

7. **When done, deactivate the virtual environment**

   ```bash
   deactivate
   ```

### What This Command Does

- **`upload-to-gcs`**: Uploads new CSV files from your local directory to the Google Cloud Storage bucket
- **`create-bigquery-tables`**: Creates BigQuery external tables for the uploaded files, allowing you to query them with SQL

---

## Future Updates

When a new version of DataWagon is released:

1. **Navigate to DataWagon directory**

   ```bash
   cd /path/to/datawagon
   ```

2. **Run the update script**

   ```bash
   ./update-venv.sh
   ```

   This automatically pulls the latest code and updates dependencies.

3. **Activate the virtual environment**

   ```bash
   source .venv/bin/activate
   ```

4. **Continue using DataWagon normally**

   ```bash
   datawagon upload-to-gcs create-bigquery-tables
   ```

---

## Troubleshooting

### Virtual Environment Not Activated

**Symptom:** You see this error:

```
-bash: datawagon: command not found
```

**Solution:** Activate the virtual environment:

```bash
source .venv/bin/activate
```

**How to tell if it's active:** Your terminal prompt should show `(.venv)` at the beginning:

```
(.venv) username@computer:~/datawagon$
```

---

### Google Cloud Authentication Errors

**Symptom:** Errors about authentication or permissions when uploading files.

**Solution:** Authenticate with Google Cloud:

```bash
gcloud auth application-default login
```

Follow the browser prompts to complete authentication.

---

### Files Not Found

**Symptom:** DataWagon reports "No files found" or "Source directory does not exist".

**Solution:** Check your `.env` configuration:

```bash
cat .env
```

Verify that `DW_CSV_SOURCE_DIR` points to the correct directory where your CSV files are located.

Example:

```
DW_CSV_SOURCE_DIR=/Users/dave/youtube_data
```

---

### Setup or Update Fails

**Symptom:** The setup or update script fails with errors.

**Solution:** Clean reinstall:

```bash
rm -rf .venv
./setup-venv.sh
source .venv/bin/activate
```

This removes the virtual environment and recreates it from scratch.

---

## Quick Reference

### First Time (Upgrading from Pre-1.0.0)

```bash
cd /path/to/datawagon
git pull
rm -rf .venv
./setup-venv.sh
source .venv/bin/activate
datawagon --help
```

### Monthly Usage

```bash
cd /path/to/datawagon
source .venv/bin/activate
datawagon upload-to-gcs create-bigquery-tables
deactivate
```

### Future Updates

```bash
cd /path/to/datawagon
./update-venv.sh
source .venv/bin/activate
```

### Check .env Settings

```bash
cat .env
```

### Get Help

```bash
datawagon --help
```

---

## Need More Help?

- Full documentation: See `README.md` in the DataWagon directory
- Developer documentation: See `CLAUDE.md` for technical details
