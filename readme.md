# DataWagon

A command line application to manage data from YouTube Analytics. Currently (v0.1.0) it supports loading CSV files, which may be compressed, into a PostgreSQL instance. 


Thre run time variables are required. They may be passed in as parameters or as environment variables. An easy way to manage them is by putting them in a `.env` file and dropping it in the top of the application folder (next to this `readme`).  




Supported file extensions: `.csv`, `.csv.gz`, `.csv.zip`



Columns added to each table begin with an underscore. ex, `_content_owner`


Order of executed operations
check_db_connection
check_files
check_database
display new files
import csv
check_database

somehow the output text should be supressed when called in pipeline