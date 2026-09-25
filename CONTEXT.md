# DataWagon

Loads YouTube Analytics report files into cloud storage so they can be queried as tables.

## Language

**Caravan**:
The company that manages the YouTube channels.

**Content Owner**:
A YouTube account whose reports Caravan receives. Some are Caravan's own (`CaravanInc`, `CaravanAffiliates`); others belong to organizations Caravan manages (`kcrw+user`).
_Avoid_: Brand, client

**Report Type**:
A kind of YouTube report, such as `claim_raw` or `asset_raw`, identified by a fixed token in the file name.
_Avoid_: Base name, file type, file selector

**Report Month**:
The calendar month a report file is issued for. Every report is monthly.
_Avoid_: File date

**Adjustment Report**:
A report of dispute-resolution corrections to earlier Report Months, issued in a later month and only when there are corrections. It is its own Report Type (e.g. `adj_claim_raw`), with the same columns as the report it corrects.
_Avoid_: Adj file, correction file

**Version**:
A revision of a Report Type's file format, marked in the file name (e.g. `v1-1`). Versions of the same Report Type are never combined.

**Storage Prefix**:
The bucket root under which every Storage Folder lives (`caravan-versioned`).

**Storage Folder**:
The bucket folder holding one Table's files, `<storage prefix>/<report type>_<version>`, partitioned by Report Month. A folder that matches no Report Type and Version is a stray, and no Table reads it.
_Avoid_: GCS folder, destination folder

**Table**:
The queryable dataset for one Report Type at one Version (e.g. `claim_raw` v1-1). A Report Type with several Versions has several Tables.
