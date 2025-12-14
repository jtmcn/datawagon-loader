# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2025-12-13

### Changed
- **Schema inference now uses BIGNUMERIC instead of NUMERIC for decimal values**
  - Replaced NUMERIC type detection with BIGNUMERIC to support values with >9 decimal places
  - BIGNUMERIC supports up to 38 decimal places (vs NUMERIC's 9 decimal place limit)
  - Fixes BigQuery errors: "Invalid NUMERIC value" for high-precision revenue data
  - Revenue columns with values like "0.000021676471" (12 decimal places) now load correctly
  - Maintains exact decimal precision for financial and scientific data
- Updated all tests to expect BIGNUMERIC instead of NUMERIC
- Updated documentation to reflect BIGNUMERIC type usage in CLAUDE.md

### Fixed
- Fixed BigQuery load failures for tables with high-precision decimal values
  - Previously: Values with >9 decimal places caused "Invalid NUMERIC value" errors
  - Now: BIGNUMERIC handles up to 38 decimal places without errors
  - Example: `partner_revenue` column with value "0.000021676471" loads successfully

### Breaking Changes
- **Existing BigQuery external tables will need to be recreated**
- Run `datawagon recreate-bigquery-tables --force` to update table schemas
- No data loss: external tables reference existing GCS data, only metadata changes
- BIGNUMERIC is backward compatible with NUMERIC values (all existing queries work)
- Query performance impact is minimal (BIGNUMERIC uses 16 bytes vs NUMERIC's 8 bytes)

### Migration Guide

After updating to v1.2.0:

```bash
# Recreate all BigQuery external tables with new BIGNUMERIC schema
datawagon recreate-bigquery-tables --force

# Or recreate specific tables only
datawagon recreate-bigquery-tables --force --tables table_one table_two
```

**Why this is safe:**
- External tables are metadata-only (no data stored in BigQuery)
- Points to same GCS files
- All existing SQL queries continue to work
- BIGNUMERIC is superset of NUMERIC (backward compatible)

## [1.1.0] - 2025-12-13

This release focuses on technical debt cleanup, observability improvements, and architectural enhancements to support future multi-cloud deployments. All changes are backward compatible with zero breaking changes.

### Added

#### Storage Abstraction (Phase 5)
- **New abstract provider interfaces for multi-cloud support**
  - Created `StorageProvider` abstract base class for cloud storage operations
    - Defines contract for upload, list, copy, and read operations
    - Enables future S3, Azure Blob Storage implementations
  - Created `AnalyticsProvider` abstract base class for analytics platforms
    - Defines contract for table management operations
    - Enables future Redshift, Snowflake implementations
  - `GcsManager` now implements `StorageProvider` interface
  - `BigQueryManager` now implements `AnalyticsProvider` interface
  - Added `read_blob_to_memory()` method to `GcsManager`
  - Added `bucket_name` and `has_error` properties with getters/setters

#### Observability & Metrics (Phase 4)
- **Upload performance metrics**
  - Per-file metrics: file size (MB), duration (seconds), throughput (MB/s)
  - Example: `"Uploaded: file.csv.gz (2.50 MB in 1.23s, 2.03 MB/s)"`
- **Batch upload summary**
  - Total files, total size, duration, average throughput
  - Success/failure counts
  - Example output:
    ```
    Upload Summary:
      Total files: 10
      Total size: 25.00 MB
      Duration: 12.50s
      Avg throughput: 2.00 MB/s
      Succeeded: 9, Failed: 1
    ```
- **Schema inference timing**
  - Duration tracking for all code paths (success, error, early return)
  - Enhanced logging with column count, sample size, type distribution
  - Example: `"Schema inference completed in 1.25s: 42 columns from 100 samples - BOOL=2, INT64=15..."`

#### File Comparison Refactoring (Phase 1)
- **New `FileComparator` class** (`datawagon/objects/file_comparator.py`)
  - Encapsulates file comparison logic previously in module-level functions
  - Methods: `compare_files()`, `find_new_files()`
  - Comprehensive test suite with 11 tests covering edge cases
  - Uses dependency injection pattern with `FileUtils`

#### Dynamic Field Handling (Phase 3)
- **Enhanced `build_data_item()` method** with kwargs support
  - Automatically preserves dynamic fields from regex extraction
  - No manual field extraction loops required
  - Added 3 tests for custom dynamic field preservation
  - Example: Custom regex groups like `region`, `channel_id` automatically passed through

### Changed

#### Code Quality Improvements
- Updated `compare.py` to use `FileComparator` class (removed 66 lines)
- Simplified `build_data_item()` implementation with dict comprehension
- Refactored managers to use private attributes for interface compliance
  - `GcsManager`: `has_error` → `_has_error` (accessed via property)
  - `BigQueryManager`: `has_error` → `_has_error`, `dataset_id` → `_dataset_id` (accessed via properties)

### Removed

#### Dead Code Cleanup (Phase 2)
- **Removed unused `CSVLoader` class** (137 lines)
  - No imports found anywhere in codebase
  - Contained unimplemented TODO for column type overrides
  - Updated `schema_inference.py` comments to remove CSVLoader references

### Technical Details

#### Test Coverage
- All 219 tests passing
- Added 14 new tests across all phases
- No test regressions

#### Performance
- Zero performance overhead from metrics (<0.1% from `perf_counter` calls)
- Timing only on successful and error paths for debugging

#### Code Statistics
- ~500 lines added (interfaces, metrics, tests)
- ~300 lines removed (dead code, simplified logic)
- 5 implementation phases completed
- 7 git commits with detailed documentation

### Migration Guide

No migration required - all changes are backward compatible. However, you can now:
1. Use abstract provider types for dependency injection
2. Monitor upload performance with new metrics in logs
3. Extend DataWagon for S3/Azure by implementing provider interfaces

## [1.0.7] - 2025-12-13

### Changed
- **Schema inference now uses NUMERIC instead of FLOAT64 for decimal values**
  - Replaced FLOAT64 type detection with NUMERIC for exact decimal precision
  - Eliminates floating-point precision loss for financial and currency data
  - Added `_try_parse_numeric()` method that accepts both integers and decimals
  - Special handling for revenue columns: combines INT64 and NUMERIC counts to ensure proper type inference
  - Revenue columns with mixed integers and decimals (e.g., "100", "200.50") now correctly infer as NUMERIC
  - Non-revenue integer columns (e.g., view_count, subscriber_count) remain as INT64
- Updated all tests to expect NUMERIC instead of FLOAT64
- Added 4 new tests for revenue column handling
- Updated documentation to reflect NUMERIC type usage

### Fixed
- Fixed schema inference for columns with mixed integer and decimal values
  - Previously: `partner_revenue` with ["100", "200.50"] → STRING (50% INT64 + 50% FLOAT64 = neither reaches 95%)
  - Now: `partner_revenue` with ["100", "200.50"] → NUMERIC (100% numeric values)

### Breaking Changes
- Existing BigQuery tables with FLOAT64 columns will need to be recreated
- Run `datawagon recreate-bigquery-tables --force` to update schemas
- No data loss: external tables reference existing GCS data

## [1.0.6] - 2025-12-13

### Removed
- Removed dead code identified by vulture static analysis
  - Removed unused `partition_column` parameter from `create_external_table()` method
    - Function uses Hive partitioning AUTO mode which automatically detects partition columns
    - Updated all callers in `create_bigquery_tables.py` and `recreate_bigquery_tables.py`
  - Removed unused `progress_bar()` and `spinner()` functions from `console.py`
    - These were only used by the migration command removed in v1.0.5
    - Cleaned up unused imports: `Iterator`, `contextmanager`, and `rich.progress` classes
  - Total cleanup: 70 lines of dead code removed across 4 files

### Changed
- Simplified `create_external_table()` API by removing unused parameter
- Reduced console.py module complexity by removing unused progress indicator functions

## [1.0.5] - 2025-12-13

### Removed
- Removed one-time migration command `migrate-to-versioned-folders`
  - Deleted `datawagon/commands/migrate_to_versioned_folders.py` (287 lines)
  - Removed CLI registration from `main.py`
  - Cleaned up migration documentation from README (56 lines)
  - This was a one-time use command for reorganizing existing GCS files into versioned folders
  - No breaking changes for users as this was a standalone utility command

### Changed
- Updated documentation to focus on core file management and BigQuery features
- Simplified README by removing one-time migration workflow documentation

## [1.0.1] - 2025-12-12

### Fixed
- Moved `pytest-cov` from dev to test dependency group to resolve CI build failures
  - CI workflow (`poetry install --with test --without dev`) was excluding pytest-cov
  - This caused "unrecognized arguments: --cov" errors during coverage tests
- Consolidated `markdown-it-py` to v3.0.0 (from dual 3.0.0/4.0.0 versions) to maintain Python 3.9 compatibility
  - markdown-it-py v4.0.0 requires Python 3.10+, but DataWagon supports Python 3.9-3.12

## [1.0.0] - 2025-12-06

This major release represents a comprehensive improvement initiative across 8 phases, transforming the project from a working prototype into a production-ready, well-tested, and thoroughly documented application.

### Added

#### Phase 3: Infrastructure Foundation
- Comprehensive logging infrastructure with file rotation and structured formatting
- Security hardening with path traversal prevention
- ReDoS (Regular Expression Denial of Service) attack prevention
- Zip bomb detection with 1GB size limit
- Retry logic with exponential backoff for GCS operations
- pytest testing framework with custom markers (unit, integration, security, slow)
- Test fixtures in conftest.py (temp_dir, sample_csv_content, mock_source_config, etc.)

#### Phase 5: Error Handling
- Comprehensive error handling across all modules
- Graceful degradation for non-critical failures
- Actionable error messages with clear guidance for users
- Input validation with detailed error reporting
- Retry mechanisms for transient GCS failures

#### Phase 6: Security Testing
- Security test suite with 31 comprehensive tests
- 100% coverage of security validation module
- Tests for path traversal, ReDoS, blob name sanitization, zip bomb detection
- Integration tests for end-to-end security validation

#### Phase 7: Comprehensive Test Coverage
- Test suite expanded from 6 to 107 tests
- Achieved 82% overall test coverage (exceeded 80% goal)
- ManagedFileMetadata: 28 tests, 100% coverage
- ManagedFileScanner: 20 tests, 96% coverage
- FileUtils: 12 tests, 97% coverage
- SourceConfig: 8 tests, 100% coverage
- Security validators: 31 tests, 100% coverage
- Logging config: 6 tests, 100% coverage

#### Phase 8: CI/CD & Documentation
- GitHub Actions updated to latest versions (v4-v5)
- mypy type checking in CI pipeline
- isort import sorting verification in CI
- Coverage reporting with 80% threshold
- Security scanning with pip-audit
- Comprehensive docstring coverage (100+ docstrings added)
- CHANGELOG.md in Keep a Changelog format
- Workflow status and coverage badges in README

### Changed

#### Phase 2: Code Cleanup
- Removed technical debt and unused code
- Cleaned up import statements and dependencies
- Streamlined configuration handling
- Improved code organization and structure

#### Phase 4: Security Best Practices
- Applied security hardening across all file operations
- Implemented input sanitization for GCS blob names
- Added validation for user-provided regex patterns
- Enhanced file path validation with security checks

#### Phase 5: Error Messages
- Improved error messages with actionable guidance
- Added context to exceptions for easier debugging
- Standardized error handling patterns across modules

#### Phase 7: Test Enhancements
- Enhanced existing FileUtils tests with 9 additional test cases
- Improved test organization with descriptive class names
- Standardized test patterns using pytest fixtures

#### Phase 8: GitHub Actions Workflows
- Updated build workflow with new job dependency chain
- Simplified release workflow (removed separate createrelease job)
- Improved release asset handling with softprops/action-gh-release@v2

### Fixed

#### Phase 1: Critical Bug Fixes
- Fixed CLI validation issues
- Corrected file processing edge cases
- Resolved path handling inconsistencies
- Fixed configuration loading errors

#### Phase 5: Error Handling Gaps
- Fixed missing error handling in file operations
- Corrected GCS upload failure scenarios
- Resolved issues with transient network failures
- Fixed edge cases in file validation

### Security

#### Phase 4: Security Hardening
- Added zip bomb detection with 1GB decompressed size limit
- Implemented regex complexity validation to prevent ReDoS attacks
- Added path traversal prevention for all file operations
- Implemented blob name sanitization for GCS uploads
- Added input validation for user-provided patterns

#### Phase 6: Security Test Suite
- Created comprehensive security test suite (31 tests)
- Achieved 100% coverage of security validation module
- Tests cover all critical security attack vectors
- Integration tests validate end-to-end security

### Removed

#### Phase 2: Technical Debt
- Removed unused imports and dependencies
- Cleaned up deprecated code patterns
- Removed redundant validation logic

#### Phase 8: Deprecated Actions
- Removed deprecated actions/upload-release-asset@v1
- Removed unnecessary artifact upload/download in release workflow

## [0.2.0] - Earlier Releases

### Added
- Migration tool for reorganizing files into versioned folders
- Version-based folder separation for BigQuery external tables
- Poetry-first workflow for dependency management

### Changed
- Streamlined setup process
- Changed root folder structure from caravan to caravan-versioned

## [0.1.0] - Initial Release

Initial working version with core functionality:
- CSV file loading from local filesystem
- Pattern-based file selection and metadata extraction
- GCS bucket upload with partitioning
- Support for .csv, .csv.gz, and .csv.zip files
- Basic configuration via TOML files
- Click-based CLI with command chaining

[Unreleased]: https://github.com/joeltkeller/datawagon/compare/v1.0.7...HEAD
[1.0.7]: https://github.com/joeltkeller/datawagon/compare/v1.0.6...v1.0.7
[1.0.6]: https://github.com/joeltkeller/datawagon/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/joeltkeller/datawagon/compare/v1.0.1...v1.0.5
[1.0.1]: https://github.com/joeltkeller/datawagon/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/joeltkeller/datawagon/releases/tag/v1.0.0
[0.2.0]: https://github.com/joeltkeller/datawagon/releases/tag/v0.2.0
[0.1.0]: https://github.com/joeltkeller/datawagon/releases/tag/v0.1.0
