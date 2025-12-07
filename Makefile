.ONESHELL:
CMD:=poetry run
PYMODULE:=datawagon
ENTRYPOINT:=main.py
TESTS:=tests


help: ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

# ============================================================================
# Setup and Installation
# ============================================================================

setup: check-poetry install-poetry-plugins check-env install-deps ## First-time setup (run this for new installations)
	@echo "✓ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Activate virtualenv: source .venv/bin/activate"
	@echo "  3. Run application: datawagon --help"

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

install-deps: ## Install dependencies with Poetry
	@echo "Installing dependencies..."
	@poetry config virtualenvs.in-project true
	@poetry install
	@echo "✓ Dependencies installed"

update: ## Update dependencies and regenerate lock file
	@echo "Updating dependencies..."
	@poetry update
	@$(MAKE) requirements
	@echo "✓ Dependencies updated"

# ============================================================================
# Code Quality Checks
# ============================================================================

pre-commit: check type isort format lint test requirements requirements-check ## Run all pre-commit checks

pre-commit-fast: type lint test ## Run faster pre-commit checks (skip format/isort)

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

requirements: ## Generate requirements.txt from poetry.lock
	@echo "Generating requirements.txt..."
	@poetry export --without-hashes -f requirements.txt -o requirements.txt
	@echo "✓ requirements.txt generated"

requirements-check: ## Verify requirements.txt is in sync with poetry.lock
	@echo "Checking if requirements.txt is in sync..."
	@poetry export --without-hashes -f requirements.txt | diff -q - requirements.txt > /dev/null || { \
		echo "⚠ requirements.txt is out of sync with poetry.lock"; \
		echo "Run 'make requirements' to update"; \
		exit 1; \
	}
	@echo "✓ requirements.txt is in sync"

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
