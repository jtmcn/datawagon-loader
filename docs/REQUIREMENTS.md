# Requirements Management

This document explains how dependencies are managed in the DataWagon loader project.

## Requirements Files

### `requirements.txt`
- **Purpose**: Production runtime dependencies only
- **Use**: Deploy to production environments
- **Install**: `pip install -r requirements.txt`
- **Contains**: Core libraries needed to run the application

### `requirements-dev.txt`
- **Purpose**: Complete development environment
- **Use**: Local development and CI/CD
- **Install**: `pip install -r requirements-dev.txt`
- **Contains**: Runtime dependencies + development tools

## Development Tools Included

### Code Quality
- **mypy** - Static type checking
- **flake8** - Code linting and style checking
- **black** - Code formatting
- **isort** - Import sorting
- **pre-commit** - Git pre-commit hooks

### Testing
- **pytest** - Testing framework
- **pytest-cov** - Coverage reporting

### Type Stubs
- **types-toml** - Type hints for toml library
- **types-tabulate** - Type hints for tabulate library
- **types-click** - Type hints for click library
- **sqlalchemy-stubs** - Type hints for SQLAlchemy

## Setup Commands

### Initial Development Setup
```bash
# Complete setup with all tools
make setup-dev

# Manual installation
pip install -r requirements-dev.txt
```

### Install Missing Tools
```bash
# Install only the development tools
make install-dev-tools
```

### Update Requirements
```bash
# Generate both requirements files from pyproject.toml
make requirements

# Check if requirements are up to date
make requirements-check
```

## Environment Support

### With Poetry (Recommended)
- Automatic dependency management
- Lock file support for reproducible builds
- Separate dependency groups (dev, test)
- Commands: `poetry install --with dev,test`

### Without Poetry (Fallback)
- Uses requirements.txt files
- Manual dependency management
- Commands: `pip install -r requirements-dev.txt`

## Validation

The build pipeline includes requirements checking:

```bash
# Full validation including requirements check
make all

# Pre-commit checks including requirements
make pre-commit

# Just check requirements
make requirements-check
```

## Best Practices

1. **Always use requirements-dev.txt for development**
2. **Keep requirements.txt minimal** (production only)
3. **Run `make requirements-check` before committing**
4. **Use `make install-dev-tools` when tools are missing**
5. **Update requirements files when adding dependencies**

## Troubleshooting

### Missing Development Tools
```bash
# Quick fix - install all dev tools
make install-dev-tools
```

### Requirements Out of Date
```bash
# With Poetry
poetry lock
make requirements

# Without Poetry
pip freeze > requirements.txt
# Manually update requirements-dev.txt
```

### Environment Issues
```bash
# Clean and rebuild
make clean-env
make setup-dev
```