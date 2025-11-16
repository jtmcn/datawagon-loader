# Testing and Validation Guide

This document explains how to use the enhanced Makefile for testing and validating the DataWagon loader project.

## Quick Start

```bash
# 🚀 Run EVERYTHING (recommended) - complete validation pipeline
make all

# Run all pre-commit checks
make pre-commit

# Run specific validation
make validate

# Run all tests
make test

# Clean cache files
make clean
```

## Available Commands

### Essential Commands

- `make all` - 🚀 **Complete validation pipeline** (structure → dependencies → quality → formatting → tests → metrics)
- `make help` - Show all available commands with descriptions
- `make pre-commit` - Quick pre-commit checks
- `make run` - Run the application
- `make test` - Run all tests
- `make clean` - Clean temporary files

### Validation Commands

- `make validate-structure` - Check project structure (e.g., __init__.py files)
- `make validate-syntax` - Check Python syntax without running code
- `make validate-imports` - Verify all imports work correctly
- `make validate` - Run all validation checks

### Testing Commands

- `make test` - Run all tests
- `make test-unit` - Run only unit tests
- `make test-integration` - Run only integration tests
- `make test-cov` - Run tests with coverage report
- `make test-failed` - Re-run only failed tests
- `make test-specific TEST=path/to/test.py` - Run specific test file

### Code Quality Commands

- `make type` - Run mypy type checking
- `make lint` - Run flake8 linting
- `make format` - Format code with black
- `make format-check` - Check formatting without modifying files
- `make isort` - Sort imports with isort
- `make isort-check` - Check import sorting without modifying files
- `make metrics` - Show code quality metrics

### Development Setup

- `make setup-dev` - Set up development environment (uses requirements-dev.txt when Poetry unavailable)
- `make install-dev-tools` - Install additional development tools (mypy, flake8, etc.)
- `make update-deps` - Update all dependencies
- `make show-deps` - Show dependency tree
- `make requirements` - Generate requirements.txt and requirements-dev.txt
- `make requirements-check` - Check if requirements files are up to date

### Requirements Files

The project uses two requirements files:
- **`requirements.txt`** - Production dependencies only (runtime)
- **`requirements-dev.txt`** - All dependencies including development tools

```bash
# For production deployment
pip install -r requirements.txt

# For development (includes testing, linting, type checking)
pip install -r requirements-dev.txt
```

### Cleaning Commands

- `make clean-cache` - Remove Python cache files (__pycache__, .pyc, etc.)
- `make clean-env` - Remove virtual environment
- `make clean-all` - Clean everything including virtual environment

## Environment Support

The Makefile automatically detects your environment:
- Works with or without Poetry
- Detects virtual environments
- Falls back to system Python if needed

## Examples

### Complete Validation Pipeline (Recommended)
```bash
make all
```
This runs the complete 7-step pipeline:
1. Clean cache files
2. Validate project structure and syntax
3. Check dependencies
4. Run code quality checks (type checking + linting)
5. Check code formatting (black + isort)
6. Run all tests
7. Generate code metrics

### Full Pre-commit Check
```bash
make pre-commit
```
This runs: dependency checks → structure validation → type checking → import sorting → code formatting → linting → tests

### Run Specific Test
```bash
make test-specific TEST=tests/test_logging_config.py
```

### Check Project Health
```bash
make validate && make metrics
```

### Clean and Rebuild
```bash
make clean-all
make setup-dev
make test
```

## Development Workflow

### Initial Setup
```bash
# Set up development environment
make setup-dev

# Or if you prefer manual setup
pip install -r requirements-dev.txt
```

### Daily Development
```bash
# Complete validation (recommended before commits)
make all

# Quick validation during development
make validate && make test

# Install missing development tools if needed
make install-dev-tools
```

### Before Committing
```bash
# Run all pre-commit checks
make pre-commit

# Or use the comprehensive pipeline
make all
```

## Tips

1. Use `make all` for comprehensive validation before commits
2. Run `make validate` to quickly catch structural issues
3. Use `make test-failed` during development to quickly re-run failing tests
4. Keep requirements files updated with `make requirements`
5. The Makefile works with both Poetry and pip environments

## Troubleshooting

If commands fail:
1. Check environment: `make help` (shows environment info)
2. Validate structure: `make validate-structure`
3. Check syntax: `make validate-syntax`
4. Clean cache: `make clean-cache`