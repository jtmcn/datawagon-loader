# DataWagon

Automated loading of YouTube Analytics files into a PostgreSQL database

### Background
This project was built to replace an existing process which used a bash file to load uncompressed files into a Postgres instance. The original script was not able to handle compressed files, and required manually moving files in and out of an import directory. It had no mechanism to check for duplicate files, and no way to check if the database was up to date with the files in the import directory. The script also required modification and manual table creation to add new types of files to the db.

### Goals
1. Leave existing process relatively intact. The user will still download the csv files and place them in a directory
2. Use the existing file storage and remove necessity of moving files in and out of an import directory
2. Allow for compressed files
3. Check for duplicate files
4. Prevent files from being imported more than once
5. Provide user feedback on the status of the import process
6. Use proper data types for each column (ie, don't use floats for revenue tracking in fractions of a cent) 


### Pipeline Setup

###### Install Application
Open `Terminall.app`
Retrieve code from GitHub
```
git clone https://github.com/jtmcn/datawagon.git
```
Move into folder
```
cd datawagon
```
Setup environment
```
./update.sh
```

###### Update Environment Variables
Three run time variables are required. They may be passed in as parameters or as environment variables. An easy way to manage them is by putting them in a `.env` file and dropping it in the top of the application folder (next to this `readme`).  

Variables:
- `DW_POSTGRES_DB_URL`
- `DW_DB_SCHEMA`
- `DW_CSV_SOURCE_DIR`



##### Typical Usage
When new files have been added to the source folder and should be copied to the database, use the following example as a guide:

```
cd ~/Code/datawagon
./update.sh # this is optional
source .venv/bin/activate
datawagon import 
```
This will check for code updates, activate the python environment, and being the import process.

When the `datawagon import` command is executed, 
It will
- check for a database connection
- prompt to create schema from `DW_DB_SCHEMA` if necessary
- check files in `DW_CSV_SOURCE_DIR` for duplicates and invalid names
- pull a list of files already uploaded from the database
- present user with comparison table for existing and new files 
- prompt and begin upload on confirmation



###### Usage Notes
- Supported file extensions: `.csv`, `.csv.gz`, `.csv.zip`
- Columns added to each table begin with an underscore. ex, `_content_owner`
