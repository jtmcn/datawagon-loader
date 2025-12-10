.ONESHELL:
# Auto-detect if Poetry is available (simple check, no expensive calls)
HAS_POETRY := $(shell command -v poetry 2> /dev/null)
ifdef HAS_POETRY
    CMD := poetry run
else
    CMD :=
endif

PYMODULE:=datawagon
ENTRYPOINT:=main.py
TESTS:=tests


help: ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

# ============================================================================
# Setup and Installation
# ============================================================================

setup: ## Auto-detect and run appropriate setup
	@if command -v poetry >/dev/null 2>&1; then \
		$(MAKE) setup-poetry; \
	else \
		$(MAKE) setup-venv; \
	fi

setup-poetry: check-poetry install-poetry-plugins check-env install-deps-poetry ## Poetry-based setup
	@echo "✓ Poetry setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Activate virtualenv: source .venv/bin/activate"
	@echo "  3. Run application: datawagon --help"

setup-venv: check-python check-env install-deps-venv verify-install ## Non-Poetry setup
	@echo "✓ Virtual environment setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Activate virtualenv: source .venv/bin/activate"
	@echo "  3. Run application: datawagon --help"

check-python: ## Check if Python 3.9+ is available
	@python3 --version | grep -qE "Python 3\.(9|1[0-2])" || { \
		echo "⚠ Python 3.9+ required"; \
		exit 1; \
	}
	@echo "✓ Python found: $$(python3 --version)"

check-poetry: ## Check if Poetry is installed
	@command -v poetry >/dev/null 2>&1 || { \
		echo "⚠ Poetry not found. Install from: https://python-poetry.org/docs/#installation"; \
		exit 1; \
	}
	@echo "✓ Poetry found: $$(poetry --version)"

install-poetry-plugins: ## Install required Poetry plugins
	@echo "Checking Poetry plugins..."
	@poetry self show plugins 2>/dev/null | grep -q "poetry-plugin-export" || { \
		echo "Installing poetry-plugin-export..."; \
		poetry self add poetry-plugin-export; \
	}
	@echo "✓ Poetry plugins ready"

check-env: ## Check if .env file exists, create from .env.example if not
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			echo "⚠ Creating .env from .env.example"; \
			cp .env.example .env; \
			echo "⚠ Please edit .env with your configuration"; \
		else \
			echo "⚠ Warning: No .env or .env.example found"; \
		fi; \
	else \
		echo "✓ .env file exists"; \
	fi

install-deps-poetry: ## Install dependencies with Poetry
	@echo "Installing dependencies..."
	@poetry config virtualenvs.in-project true
	@poetry install
	@echo "✓ Dependencies installed"

install-deps-venv: ## Install dependencies with pip (non-Poetry)
	@echo "Creating virtual environment..."
	@python3 -m venv .venv
	@echo "Installing datawagon and dependencies..."
	@.venv/bin/pip install --upgrade pip --quiet
	@.venv/bin/pip install -e . --quiet
	@echo "✓ Runtime dependencies installed (dev tools not included)"
	@echo "  For development, use Poetry: make setup-poetry"

verify-install: ## Verify DataWagon installation
	@echo "→ Verifying DataWagon installation..."
	@if [ ! -d ".venv" ]; then \
		echo "✗ Virtual environment not found"; \
		echo "→ Run './setup-venv.sh' or 'make setup' first"; \
		exit 1; \
	fi
	@.venv/bin/python -c "import datawagon" 2>/dev/null || { \
		echo "✗ Failed to import datawagon"; \
		exit 1; \
	}
	@.venv/bin/datawagon --help >/dev/null 2>&1 || { \
		echo "✗ datawagon command failed"; \
		exit 1; \
	}
	@echo "✓ Installation verified"
	@echo ""
	@if command -v poetry >/dev/null 2>&1 && [ -f "poetry.lock" ]; then \
		echo "Type: Poetry-managed"; \
	else \
		echo "Type: Standard venv (runtime-only)"; \
	fi

update: ## Update dependencies and regenerate lock file
	@echo "Updating dependencies..."
	@poetry update
	@$(MAKE) requirements
	@echo "✓ Dependencies updated"

# ============================================================================
# Code Quality Checks
# ============================================================================

pre-commit: check type isort format lint shellcheck test requirements requirements-check ## Run all pre-commit checks

pre-commit-fast: type lint shellcheck test ## Run faster pre-commit checks (skip format/isort)

check:
	@echo "Checking poetry..."
	poetry check

type: ## Type check code
	@echo "Type checking with mypy..."
	$(CMD) mypy --namespace-packages --explicit-package-bases $(PYMODULE) $(TESTS)

isort: ## Sort imports
	@echo "Sorting imports with isort..."
	$(CMD) isort --quiet --recursive $(PYMODULE) $(TESTS)

format: ## Format code
	@echo "Formatting code with black..."
	$(CMD) black $(PYMODULE) $(TESTS)

lint: ## Lint code
	@echo "Linting code with flake8..."
	$(CMD) flake8 $(PYMODULE) $(TESTS)

vulture: ## Detect dead code
	@echo "Detecting dead code with vulture..."
	$(CMD) vulture $(PYMODULE) --min-confidence 70

test: ## Run tests
	@echo "Running tests with pytest..."
	$(CMD) pytest $(TESTS) --quiet

shellcheck: ## Lint shell scripts with shellcheck
	@echo "Linting shell scripts with shellcheck..."
	@if ! command -v shellcheck >/dev/null 2>&1; then \
		echo "⚠ shellcheck not found - install from: https://www.shellcheck.net/"; \
		exit 1; \
	fi
	@shellcheck setup-venv.sh update-venv.sh update.sh || { \
		echo "⚠ Shell script linting failed"; \
		exit 1; \
	}
	@echo "✓ Shell scripts passed linting"

requirements: ## Generate requirements.txt and requirements-dev.txt from poetry.lock
	@echo "Generating requirements.txt..."
	@( \
		echo "# AUTO-GENERATED FILE - DO NOT EDIT MANUALLY"; \
		echo "# Generated from poetry.lock using 'make requirements'"; \
		echo "# To update: modify pyproject.toml, run 'poetry lock', then 'make requirements'"; \
		echo "#"; \
		echo "# Generated: $$(date -u '+%Y-%m-%d %H:%M:%S UTC')"; \
		echo ""; \
		poetry export --without-hashes -f requirements.txt; \
	) > requirements.txt
	@echo "Generating requirements-dev.txt..."
	@( \
		echo "# AUTO-GENERATED FILE - DO NOT EDIT MANUALLY"; \
		echo "# Generated from poetry.lock using 'make requirements'"; \
		echo "# Includes: runtime + dev + test dependencies"; \
		echo "#"; \
		echo "# Generated: $$(date -u '+%Y-%m-%d %H:%M:%S UTC')"; \
		echo ""; \
		poetry export --with dev --with test --without-hashes -f requirements.txt; \
	) > requirements-dev.txt
	@echo "✓ requirements files generated"

requirements-check: ## Verify requirements files in sync with poetry.lock
	@if ! command -v poetry >/dev/null 2>&1; then \
		echo "ℹ Skipping requirements sync check"; \
		echo "  (Poetry not installed - check only needed for Poetry users)"; \
		exit 0; \
	fi
	@echo "Checking requirements.txt sync..."
	@TMP1=$$(mktemp); TMP2=$$(mktemp); \
	grep -v '^#' requirements.txt | grep -v '^$$' > "$$TMP1"; \
	poetry export --without-hashes -f requirements.txt > "$$TMP2"; \
	DIFF_OUT=$$(diff -u "$$TMP1" "$$TMP2" 2>&1); \
	rm -f "$$TMP1" "$$TMP2"; \
	if [ -n "$$DIFF_OUT" ]; then \
		echo "⚠ requirements.txt out of sync with poetry.lock"; \
		echo ""; \
		echo "Differences found:"; \
		echo "$$DIFF_OUT" | head -20; \
		if [ $$(echo "$$DIFF_OUT" | wc -l) -gt 20 ]; then \
			echo "... (output truncated, showing first 20 lines)"; \
		fi; \
		echo ""; \
		echo "To fix: make requirements"; \
		exit 1; \
	fi
	@echo "Checking requirements-dev.txt sync..."
	@TMP1=$$(mktemp); TMP2=$$(mktemp); \
	grep -v '^#' requirements-dev.txt | grep -v '^$$' > "$$TMP1"; \
	poetry export --with dev --with test --without-hashes -f requirements.txt > "$$TMP2"; \
	DIFF_OUT=$$(diff -u "$$TMP1" "$$TMP2" 2>&1); \
	rm -f "$$TMP1" "$$TMP2"; \
	if [ -n "$$DIFF_OUT" ]; then \
		echo "⚠ requirements-dev.txt out of sync with poetry.lock"; \
		echo ""; \
		echo "Differences found:"; \
		echo "$$DIFF_OUT" | head -20; \
		if [ $$(echo "$$DIFF_OUT" | wc -l) -gt 20 ]; then \
			echo "... (output truncated, showing first 20 lines)"; \
		fi; \
		echo ""; \
		echo "To fix: make requirements"; \
		exit 1; \
	fi
	@echo "✓ Requirements files in sync"

# ============================================================================
# Application Commands (not used for automation)
# ============================================================================

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

clean-env: ## Remove virtual environment
	@echo "Cleaning up virtual environment..."
	rm -rf .venv

clean-build: ## Remove build artifacts
	@echo "Cleaning build artifacts..."
	rm -rf dist/ build/ *.egg-info

clean: clean-env clean-build ## Remove all generated files
