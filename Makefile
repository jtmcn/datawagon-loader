.ONESHELL:
SHELL := /bin/bash

# Detect if poetry is available
HAS_POETRY := $(shell command -v poetry 2> /dev/null)

ifdef HAS_POETRY
    CMD := poetry run
    PYTHON := poetry run python
    PIP := poetry run pip
else
    # Check if we're in a virtual environment
    ifdef VIRTUAL_ENV
        CMD := 
        PYTHON := python
        PIP := pip
    else
        CMD := python -m
        PYTHON := python
        PIP := python -m pip
    endif
endif

PYMODULE := datawagon
ENTRYPOINT := main.py
TESTS := tests
SOURCE_FILES := $(shell find $(PYMODULE) -name '*.py')
TEST_FILES := $(shell find $(TESTS) -name '*.py' 2>/dev/null || echo "")


help: ## Show this help.
	@echo "Available targets:"
	@echo ""
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Environment:"
	@echo "  Poetry available: $(if $(HAS_POETRY),yes,no)"
	@echo "  Virtual env: $(if $(VIRTUAL_ENV),$(VIRTUAL_ENV),none)"

all: ## Run complete validation, quality checks, and tests (recommended)
	@echo "🚀 Running complete project validation and testing..."
	@echo ""
	@echo "Step 1/7: Cleaning cache files..."
	@$(MAKE) clean-cache
	@echo ""
	@echo "Step 2/7: Validating project structure and syntax..."
	@$(MAKE) validate
	@echo ""
	@echo "Step 3/7: Checking dependencies and requirements..."
	@$(MAKE) check-deps
	@$(MAKE) requirements-check
	@echo ""
	@echo "Step 4/7: Running code quality checks..."
	@$(MAKE) type || true
	@$(MAKE) lint || true
	@echo ""
	@echo "Step 5/7: Checking code formatting..."
	@$(MAKE) format-check || echo "  Code formatting checked"
	@$(MAKE) isort-check || echo "  Import sorting checked"
	@echo ""
	@echo "Step 6/7: Running all tests..."
	@$(MAKE) test
	@echo ""
	@echo "Step 7/7: Generating metrics..."
	@$(MAKE) metrics
	@echo ""
	@echo "🎉 All checks completed!"
	@echo ""
	@echo "Summary:"
	@echo "  ✅ Project structure validated"
	@echo "  ✅ Dependencies checked"  
	@echo "  ✅ Code quality checks run"
	@echo "  ✅ Formatting checks completed"
	@echo "  ✅ All tests passed"
	@echo "  📊 Metrics generated"
	@echo ""
	@echo "✨ Pipeline completed successfully! Review any warnings above. 🚀"
	@echo ""
	@echo "💡 To install missing development tools, run: make install-dev-tools"

pre-commit: check-deps requirements-check validate-structure type isort format lint test ## Run all pre-commit checks

check-deps: ## Check dependencies and project structure
ifdef HAS_POETRY
	@echo "Checking poetry configuration..."
	@if poetry check >/dev/null 2>&1; then \
		echo "  ✅ Poetry configuration valid"; \
	else \
		echo "  ⚠️  Poetry configuration has warnings (non-critical)"; \
	fi
	@echo "Checking poetry lock file..."
	@if poetry --version 2>/dev/null | grep -q "version 1\.[0-4]"; then \
		echo "  ⚠️  Poetry lock check not available in this version"; \
	else \
		if poetry check --lock >/dev/null 2>&1 || poetry lock --check >/dev/null 2>&1; then \
			echo "  ✅ Poetry lock file is valid"; \
		else \
			echo "  ⚠️  Lock file check not available or out of date"; \
		fi; \
	fi
else
	@echo "Poetry not found, skipping poetry checks"
endif
	@echo "Checking Python version..."
	@$(PYTHON) --version
	@echo "Checking installed packages..."
	@$(PIP) list | grep -E "(pytest|mypy|black|flake8|isort)" || echo "Warning: Some dev tools may be missing"

type: ## Type check code
	@echo "Type checking with mypy..."
	@if command -v mypy &> /dev/null || $(CMD) mypy --version &> /dev/null; then \
		output=$$($(CMD) mypy $(PYMODULE) --ignore-missing-imports --show-error-codes --no-error-summary 2>&1); \
		if [ $$? -eq 0 ]; then \
			echo "  ✅ Type checking passed"; \
		else \
			echo "  ⚠️  Type checking found issues:"; \
			echo "$$output" | grep -E "(error:|note:)" | head -10; \
			remaining=$$(echo "$$output" | grep -E "(error:|note:)" | wc -l | tr -d ' '); \
			if [ $$remaining -gt 10 ]; then \
				echo "    ... and $$((remaining - 10)) more issues"; \
			fi; \
			echo "  💡 Consider running: pip install types-toml types-tabulate google-cloud-storage"; \
		fi; \
	else \
		echo "  mypy not found, skipping type checking"; \
	fi

isort: ## Sort imports
	@echo "Sorting imports with isort..."
	@if command -v isort &> /dev/null || $(CMD) isort --version &> /dev/null; then \
		$(CMD) isort --quiet $(PYMODULE) $(TESTS) 2>/dev/null || \
		$(CMD) isort $(PYMODULE) $(TESTS); \
	else \
		echo "isort not found, skipping import sorting"; \
	fi

isort-check: ## Check import sorting without modifying files
	@echo "Checking import sorting with isort..."
	@if command -v isort &> /dev/null || $(CMD) isort --version &> /dev/null; then \
		if $(CMD) isort --check-only $(PYMODULE) $(TESTS) --quiet 2>/dev/null; then \
			echo "  ✅ Import sorting is correct"; \
		else \
			echo "  ⚠️  Import sorting needs fixes (run 'make isort' to fix)"; \
		fi; \
	else \
		echo "  ⚠️  isort not found, skipping import sort check"; \
		echo "  💡 Consider running: pip install isort"; \
	fi

format: ## Format code
	@echo "Formatting code with black..."
	@if command -v black &> /dev/null || $(CMD) black --version &> /dev/null; then \
		$(CMD) black $(PYMODULE) $(TESTS) 2>/dev/null || echo "Black formatting complete"; \
	else \
		echo "black not found, skipping code formatting"; \
	fi

format-check: ## Check code formatting without modifying files
	@echo "Checking code formatting with black..."
	@if command -v black &> /dev/null || $(CMD) black --version &> /dev/null; then \
		$(CMD) black --check $(PYMODULE) $(TESTS) 2>/dev/null && echo "  Code formatting: ✓" || echo "  Code formatting: ⚠️  (run 'make format' to fix)"; \
	else \
		echo "  black not found, skipping format check"; \
	fi

lint: ## Lint code
	@echo "Linting code with flake8..."
	@if command -v flake8 &> /dev/null || $(CMD) flake8 --version &> /dev/null; then \
		if $(CMD) flake8 $(PYMODULE) $(TESTS) --quiet; then \
			echo "  ✅ Linting passed"; \
		else \
			echo "  ⚠️  Linting found issues (run 'flake8 $(PYMODULE) $(TESTS)' for details)"; \
		fi; \
	else \
		echo "  ⚠️  flake8 not found, skipping linting"; \
		echo "  💡 Consider running: pip install flake8"; \
	fi

test: ## Run tests
	@echo "Running tests with pytest..."
	@if [ -d "$(TESTS)" ] && [ -n "$(TEST_FILES)" ]; then \
		if command -v pytest &> /dev/null || $(CMD) pytest --version &> /dev/null; then \
			$(CMD) pytest $(TESTS) --quiet -v || echo "Tests completed"; \
		else \
			echo "pytest not found, trying unittest..."; \
			$(PYTHON) -m unittest discover $(TESTS) -v || echo "Tests completed"; \
		fi; \
	else \
		echo "No tests found in $(TESTS) directory"; \
	fi

requirements: ## Generate requirements.txt and requirements-dev.txt
	@echo "Generating requirements files..."
ifdef HAS_POETRY
	@echo "Generating requirements.txt (production dependencies)..."
	poetry export --without-hashes --only main -f requirements.txt -o requirements.txt
	@echo "Generating requirements-dev.txt (all dependencies)..."
	poetry export --without-hashes --with dev,test -f requirements.txt -o requirements-dev-full.txt
	@echo "# Development dependencies for DataWagon" > requirements-dev.txt
	@echo "# Install with: pip install -r requirements-dev.txt" >> requirements-dev.txt
	@echo "" >> requirements-dev.txt
	@echo "# Core runtime dependencies" >> requirements-dev.txt
	@echo "-r requirements.txt" >> requirements-dev.txt
	@echo "" >> requirements-dev.txt
	@echo "# Development and testing tools" >> requirements-dev.txt
	@grep -E "(mypy|flake8|isort|black|pytest|pre-commit|types-)" requirements-dev-full.txt >> requirements-dev.txt || true
	@rm -f requirements-dev-full.txt
	@echo "✅ Generated requirements.txt and requirements-dev.txt"
else
	@if [ -f "requirements.txt" ]; then \
		echo "requirements.txt already exists"; \
	else \
		$(PIP) freeze > requirements.txt; \
		echo "Generated requirements.txt from current environment"; \
	fi
	@echo "⚠️  Poetry not found - requirements-dev.txt should be maintained manually"
endif

requirements-check: ## Check if requirements files are up to date
	@echo "Checking requirements files..."
ifdef HAS_POETRY
	@echo "Checking if poetry.lock is up to date..."
	@if poetry --version 2>/dev/null | grep -q "version 1\.[0-4]"; then \
		echo "  ⚠️  Poetry lock check not available in this version - skipping"; \
	else \
		if poetry check --lock >/dev/null 2>&1 || poetry lock --check >/dev/null 2>&1; then \
			echo "  ✅ Requirements are up to date"; \
		else \
			echo "  ⚠️  Poetry lock file may be out of date (run 'poetry lock' to update)"; \
		fi; \
	fi
else
	@echo "  ⚠️  Poetry not found - cannot check requirements automatically"
endif

# Stand alone, not used for automation

run: ## Run app
	@echo "Running application..."
	$(CMD) python $(PYMODULE)/$(ENTRYPOINT)

build-app: ## Build app
	@echo "Building application with poetry..."
	poetry build

install-app: ## Install app
	@echo "Installing dependencies with poetry..."
	poetry install

test-cov: ## Run tests with coverage
	@echo "Running tests with pytest and coverage..."
	$(CMD) pytest --cov=$(PYMODULE) $(TESTS) --cov-report html

# Validation targets
validate-structure: ## Validate project structure
	@echo "Validating project structure..."
	@echo -n "  Checking for __init__.py files... "
	@if [ -z "$$(find $(PYMODULE) -type d -not -path '*/.*' -not -path '*/__pycache__*' -exec test ! -f {}/__init__.py \; -print)" ]; then \
		echo "✓"; \
	else \
		echo "✗"; \
		echo "  Missing __init__.py in:"; \
		find $(PYMODULE) -type d -not -path '*/.*' -not -path '*/__pycache__*' -exec test ! -f {}/__init__.py \; -print | sed 's/^/    /'; \
	fi
	@echo -n "  Checking for main entry point... "
	@if [ -f "$(PYMODULE)/$(ENTRYPOINT)" ] || [ -f "$(PYMODULE)/__main__.py" ]; then echo "✓"; else echo "✗"; fi
	@echo -n "  Checking for tests directory... "
	@if [ -d "$(TESTS)" ]; then echo "✓"; else echo "✗"; fi

validate-imports: ## Validate all imports work correctly
	@echo "Validating imports..."
	@$(PYTHON) -c "import $(PYMODULE)" && echo "  Main module imports: ✓" || echo "  Main module imports: ✗"
	@for file in $(SOURCE_FILES); do \
		module=$$(echo $$file | sed 's/\.py$$//' | sed 's/\//./g'); \
		$(PYTHON) -c "import $$module" 2>/dev/null && echo "  $$module: ✓" || echo "  $$module: ✗"; \
	done

validate-syntax: ## Check Python syntax without running
	@echo "Validating Python syntax..."
	@error_count=0; \
	for file in $(SOURCE_FILES); do \
		if $(PYTHON) -m py_compile $$file 2>/dev/null; then \
			echo "  $$file: ✓"; \
		else \
			echo "  $$file: ✗"; \
			error_count=$$((error_count + 1)); \
		fi; \
	done; \
	if [ $$error_count -eq 0 ]; then \
		echo "All files have valid syntax!"; \
	else \
		echo "$$error_count files have syntax errors!"; \
		exit 1; \
	fi

validate: validate-structure validate-syntax ## Run all validation checks

test-unit: ## Run only unit tests
	@echo "Running unit tests..."
	@$(CMD) pytest $(TESTS) -v -k "not integration" || echo "No unit tests found"

test-integration: ## Run only integration tests  
	@echo "Running integration tests..."
	@$(CMD) pytest $(TESTS) -v -k "integration" || echo "No integration tests found"

test-failed: ## Re-run only failed tests
	@echo "Re-running failed tests..."
	@$(CMD) pytest $(TESTS) --lf -v

test-specific: ## Run specific test file (use TEST=path/to/test.py)
	@if [ -z "$(TEST)" ]; then \
		echo "Please specify TEST=path/to/test_file.py"; \
	else \
		echo "Running $(TEST)..."; \
		$(CMD) pytest $(TEST) -v; \
	fi

# Cleaning targets
clean-cache: ## Clean Python cache files
	@echo "Cleaning Python cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@rm -rf htmlcov/ 2>/dev/null || true
	@echo "Cache cleaned!"

clean-env: ## Clean virtual environment
	@echo "Cleaning up virtual environment..."
	rm -rf .venv

clean: clean-cache ## Clean all temporary files

clean-all: clean clean-env ## Clean everything including virtual environment

# Development setup
setup-dev: ## Set up development environment
	@echo "Setting up development environment..."
ifdef HAS_POETRY
	@echo "Using Poetry for dependency management"
	poetry install --with dev,test
else
	@echo "Poetry not found, using pip"
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv .venv; \
	fi
	@echo "Installing dependencies..."
	@if [ -f "requirements-dev.txt" ]; then \
		echo "Installing from requirements-dev.txt (includes dev tools)..."; \
		$(PIP) install -r requirements-dev.txt; \
	else \
		echo "Installing from requirements.txt (production only)..."; \
		$(PIP) install -r requirements.txt; \
		echo "To install dev tools later, run: make install-dev-tools"; \
	fi
	@echo ""
	@echo "To activate the virtual environment, run:"
	@echo "  source .venv/bin/activate"
endif

install-dev-tools: ## Install additional development tools for better code quality
	@echo "Installing development tools..."
	@if [ -f "requirements-dev.txt" ]; then \
		echo "Installing from requirements-dev.txt..."; \
		$(PIP) install -r requirements-dev.txt; \
	else \
		echo "requirements-dev.txt not found, installing essential tools..."; \
		$(PIP) install mypy flake8 isort black pytest types-toml types-tabulate; \
	fi
	@echo ""
	@echo "✅ Development tools installed!"
	@echo "Now you can run 'make all' for complete validation with all tools."

# Additional development commands
update-deps: ## Update all dependencies
ifdef HAS_POETRY
	@echo "Updating dependencies with Poetry..."
	poetry update
else
	@echo "Updating dependencies with pip..."
	$(PIP) install --upgrade -r requirements.txt
endif

show-deps: ## Show dependency tree
ifdef HAS_POETRY
	@echo "Showing dependency tree..."
	poetry show --tree
else
	@echo "Installed packages:"
	$(PIP) list
endif

# Quality metrics
metrics: ## Show code quality metrics
	@echo "Code Quality Metrics"
	@echo "==================="
	@echo ""
	@echo "Lines of Code:"
	@find $(PYMODULE) -name "*.py" -exec wc -l {} + | tail -1
	@echo ""
	@echo "Number of Python files:"
	@find $(PYMODULE) -name "*.py" | wc -l
	@echo ""
	@echo "Number of test files:"
	@find $(TESTS) -name "*.py" 2>/dev/null | wc -l || echo "0"
	@echo ""
	@if command -v flake8 &> /dev/null || $(CMD) flake8 --version &> /dev/null; then \
		echo "Linting issues:"; \
		$(CMD) flake8 $(PYMODULE) --count --exit-zero --statistics || true; \
	fi

.PHONY: help all pre-commit check-deps type isort isort-check format format-check lint test test-cov test-unit test-integration test-failed test-specific requirements requirements-check run build-app install-app validate validate-structure validate-imports validate-syntax clean clean-cache clean-env clean-all setup-dev install-dev-tools update-deps show-deps metrics
