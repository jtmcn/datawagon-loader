# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/joeltkeller/datawagon/compare/v1.0.6...HEAD
[1.0.6]: https://github.com/joeltkeller/datawagon/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/joeltkeller/datawagon/compare/v1.0.1...v1.0.5
[1.0.1]: https://github.com/joeltkeller/datawagon/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/joeltkeller/datawagon/releases/tag/v1.0.0
[0.2.0]: https://github.com/joeltkeller/datawagon/releases/tag/v0.2.0
[0.1.0]: https://github.com/joeltkeller/datawagon/releases/tag/v0.1.0
