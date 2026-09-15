# One Table per Version

YouTube changes a report's columns between Versions (e.g. `claim_raw` v1-0 vs v1-1), so a single table could not hold every Version's schema. Each Version of a Report Type gets its own storage folder and its own BigQuery external table (`claim_raw_v1_1`), and Versions are never combined, rather than one table per Report Type with a version column.
