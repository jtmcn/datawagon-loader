# DataWagon Loader

## Project Overview

This project, "DataWagon Loader," is a Python command-line interface (CLI) application designed to automate the ingestion and upload of YouTube Analytics CSV files to Google Cloud Storage (GCS). It is built with Python 3.9+, using the `click` library for the CLI, `poetry` for dependency management, and the `google-cloud-storage` library for interacting with GCS.

The application is designed to be run from the command line, and it provides several commands for managing and uploading files. It uses a TOML file (`datawagon-config.toml`) for configuring how different types of files are processed, including how to extract metadata from filenames using regular expressions.

## Building and Running

The project uses `poetry` for dependency management and `pre-commit` for code quality checks.

### Setup

1.  **Install dependencies:**
    ```bash
    poetry install
    ```

2.  **Set up pre-commit hooks:**
    ```bash
    pre-commit install
    ```

### Running the Application

The application requires several environment variables to be set, which can be placed in a `.env` file in the project root:

*   `DW_CSV_SOURCE_DIR`: The directory containing the YouTube Analytics CSV files.
*   `DW_CSV_SOURCE_TOML`: The path to the `datawagon-config.toml` file.
*   `DW_GCS_PROJECT_ID`: The Google Cloud Storage project ID.
*   `DW_GCS_BUCKET`: The Google Cloud Storage bucket name.

Once the environment variables are set, you can run the application using the `datawagon` command:

```bash
poetry run datawagon --help
```

### Available Commands

*   `files-in-local-fs`: List files in the local filesystem.
*   `files-in-storage`: List files already in the GCS bucket.
*   `compare-local-files-to-bucket`: Compare local files to the bucket to see what's new.
*   `upload-to-gcs`: Upload new files to GCS.
*   `file-zip-to-gzip`: Convert zip files to gzip format.

### Testing

The project uses `pytest` for testing. To run the tests:

```bash
poetry run pytest
```

## Development Conventions

*   **Dependency Management:** The project uses `poetry` to manage dependencies. Add new dependencies to the `pyproject.toml` file and then run `poetry install`.
*   **Code Style:** The project uses `black` for code formatting and `flake8` for linting. These are enforced by pre-commit hooks.
*   **Type Hinting:** The project uses type hints, and `mypy` is used for static type checking.
*   **CLI:** The command-line interface is built using the `click` library. New commands should be added to the `datawagon/commands` directory and registered in `datawagon/main.py`.
*   **Configuration:** The application is configured through environment variables and the `datawagon-config.toml` file.
*   **GCS Interaction:** All interactions with Google Cloud Storage are handled by the `GcsManager` class in `datawagon/bucket/gcs_manager.py`.
