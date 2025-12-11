# DataWagon User Guide for Gordon (Windows)

## About This Guide

This guide is for **monthly DataWagon usage on Windows**. It covers:
- One-time setup (upgrading from pre-1.0.0)
- Monthly workflow for uploading files and creating BigQuery tables
- Future update process
- Basic troubleshooting

You won't need to write any code or use development tools. Just follow the simple steps below.

**Important:** Use **Command Prompt (cmd.exe)**, not PowerShell. See troubleshooting section if you need help finding Command Prompt.

---

## One-Time Setup (Upgrading from Pre-1.0.0)

Follow these steps to upgrade your existing DataWagon installation:

1. **Open Command Prompt (cmd.exe)**

   Press `Windows Key + R`, type `cmd`, and press Enter.

2. **Navigate to your DataWagon directory**
   ```batch
   cd C:\path\to\datawagon
   ```
   Replace `C:\path\to\datawagon` with your actual path

3. **Pull the latest changes**
   ```batch
   git pull
   ```

4. **Remove the old virtual environment**
   ```batch
   rmdir /s /q .venv
   ```

5. **Run the setup script**
   ```batch
   setup-venv.bat
   ```
   This will take about 30 seconds and install all necessary dependencies.

6. **Activate the virtual environment**
   ```batch
   .venv\Scripts\activate.bat
   ```
   You should see `(.venv)` appear at the start of your command prompt.

7. **Verify the installation**
   ```batch
   datawagon --help
   ```
   You should see a list of available commands.

**Important:** Your existing `.env` file will be preserved automatically. You don't need to reconfigure it.

---

## Monthly Usage

This is your regular workflow for uploading new YouTube Analytics files:

1. **Open Command Prompt (cmd.exe)**

   Press `Windows Key + R`, type `cmd`, and press Enter.

2. **Navigate to DataWagon directory**
   ```batch
   cd C:\path\to\datawagon
   ```

3. **Activate the virtual environment**
   ```batch
   .venv\Scripts\activate.bat
   ```
   Look for `(.venv)` at the start of your prompt to confirm it's active.

4. **Run the monthly command**
   ```batch
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
   ```batch
   deactivate
   ```

### What This Command Does

- **`upload-to-gcs`**: Uploads new CSV files from your local directory to the Google Cloud Storage bucket
- **`create-bigquery-tables`**: Creates BigQuery external tables for the uploaded files, allowing you to query them with SQL

---

## Future Updates

When a new version of DataWagon is released:

1. **Navigate to DataWagon directory**
   ```batch
   cd C:\path\to\datawagon
   ```

2. **Run the update script**
   ```batch
   update-venv.bat
   ```
   This automatically pulls the latest code and updates dependencies.

3. **Activate the virtual environment**
   ```batch
   .venv\Scripts\activate.bat
   ```

4. **Continue using DataWagon normally**
   ```batch
   datawagon upload-to-gcs create-bigquery-tables
   ```

---

## Troubleshooting

### Virtual Environment Not Activated

**Symptom:** You see this error:
```
'datawagon' is not recognized as an internal or external command,
operable program or batch file.
```

**Solution:** Activate the virtual environment:
```batch
.venv\Scripts\activate.bat
```

**How to tell if it's active:** Your command prompt should show `(.venv)` at the beginning:
```
(.venv) C:\datawagon>
```

---

### Google Cloud Authentication Errors

**Symptom:** Errors about authentication or permissions when uploading files.

**Solution:** Authenticate with Google Cloud:
```batch
gcloud auth application-default login
```

Follow the browser prompts to complete authentication.

---

### Files Not Found

**Symptom:** DataWagon reports "No files found" or "Source directory does not exist".

**Solution:** Check your `.env` configuration:
```batch
type .env
```

Verify that `DW_CSV_SOURCE_DIR` points to the correct directory where your CSV files are located.

Example:
```
DW_CSV_SOURCE_DIR=C:\Users\Gordon\youtube_data
```

**Note:** Use forward slashes or double backslashes in paths:
```
DW_CSV_SOURCE_DIR=C:/Users/Gordon/youtube_data
```
or
```
DW_CSV_SOURCE_DIR=C:\\Users\\Gordon\\youtube_data
```

---

### Setup or Update Fails

**Symptom:** The setup or update script fails with errors.

**Solution:** Clean reinstall:
```batch
rmdir /s /q .venv
setup-venv.bat
.venv\Scripts\activate.bat
```

This removes the virtual environment and recreates it from scratch.

---

### PowerShell Errors

**Symptom:** You're using PowerShell and seeing errors like:
```
cannot be loaded because running scripts is disabled on this system
```

**Solution:** Use Command Prompt (cmd.exe) instead of PowerShell.

Our scripts are `.bat` files designed for Command Prompt, not PowerShell's `.ps1` format.

**How to open Command Prompt:**
1. Press `Windows Key + R`
2. Type: `cmd`
3. Press Enter

---

### Python Not Found

**Symptom:** Setup script fails with:
```
'python' is not recognized as an internal or external command
```

**Solution:** Python is not in your PATH. Try:
```batch
py --version
```

If that works, Python is installed but using the launcher. The setup script should handle this automatically.

If neither works, you may need to reinstall Python and ensure "Add Python to PATH" is checked during installation.

---

## Quick Reference

### First Time (Upgrading from Pre-1.0.0)
```batch
cd C:\path\to\datawagon
git pull
rmdir /s /q .venv
setup-venv.bat
.venv\Scripts\activate.bat
datawagon --help
```

### Monthly Usage
```batch
cd C:\path\to\datawagon
.venv\Scripts\activate.bat
datawagon upload-to-gcs create-bigquery-tables
deactivate
```

### Future Updates
```batch
cd C:\path\to\datawagon
update-venv.bat
.venv\Scripts\activate.bat
```

### Check .env Settings
```batch
type .env
```

### Get Help
```batch
datawagon --help
```

---

## Need More Help?

- Full documentation: See `README.md` in the DataWagon directory
- Developer documentation: See `CLAUDE.md` for technical details
- GitHub Issues: https://github.com/joeltkeller/datawagon/issues
