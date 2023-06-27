# DataWagon

Automated loading of YouTube Analytics files into a PostgreSQL database

##### Background
This project was built to replace an existing process which used a bash file to load uncompressed files into a Postgres instance. The original script was not able to handle compressed files, and required manually moving files in and out of an import directory. It had no mechanism to check for duplicate files, and no way to check if the database was up to date with the files in the import directory. The script also required modification and manual table creation to add new types of files to the db.

##### Goals
1. Leave existing process relatively intact. The user will still download the csv files and place them in a directory
2. Use the existing file storage and remove necessity of moving files in and out of an import directory
2. Allow for compressed files
3. Check for duplicate files
4. Prevent files from being imported more than once


##### Setup

###### Install
Install Poetry
`curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -`

Run `make setup` to install dependencies

Run `make install` to install the package as a command line tool

###### Usage
Supported file extensions: `.csv`, `.csv.gz`, `.csv.zip`

###### Database
Columns added to each table begin with an underscore. ex, `_content_owner`


###### Environment Variables
Three run time variables are required. They may be passed in as parameters or as environment variables. An easy way to manage them is by putting them in a `.env` file and dropping it in the top of the application folder (next to this `readme`).  

Variables:
`DW_POSTGRES_DB_URL`
`DW_DB_SCHEMA`
`DW_CSV_SOURCE_DIR`



Order of executed operations
check_db_connection
check_files
check_database
display new files
import csv
check_database
