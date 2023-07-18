.ONESHELL:
CMD:=poetry run
PYMODULE:=datawagon
ENTRYPOINT:=main.py
TESTS:=tests


help: ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

pre-commit: check type isort format lint test  ## Run pre-commit checks

requirements: ## Generate requirements.txt
	@echo "Generating requirements.txt"
	poetry export --without-hashes -f requirements.txt -o requirements.txt

check:
	@echo "Checking poetry"
	poetry check

type: ## Type check code
	@echo "Type checking with mypy"
	$(CMD) mypy --namespace-packages --explicit-package-bases $(PYMODULE) $(TESTS)

isort: ## Sort imports
	@echo "Sorting imports with isort"
	$(CMD) isort --recursive $(PYMODULE) $(TESTS)

format: ## Format code
	@echo "Formatting code with black"
	$(CMD) black $(PYMODULE) $(TESTS)

lint: ## Lint code
	@echo "Linting code with flake8"
	$(CMD) flake8 $(PYMODULE) $(TESTS)

test: ## Run tests
	@echo "Running tests with pytest"
	$(CMD) pytest $(TESTS) --quiet


# Stand alone, not used for automation

run: ## Run app
	@echo "Running application"
	$(CMD) python $(PYMODULE)/$(ENTRYPOINT)

build-app: ## Build app
	@echo "Building application with poetry"
	poetry build

install-app: ## Install app
	@echo "Installing dependencies with poetry"
	poetry install

test-cov: ## Run tests with coverage
	@echo "Running tests with pytest and coverage"
	$(CMD) pytest --cov=$(PYMODULE) $(TESTS) --cov-report html

build-binary: ## Build binary
	@echo "Building binary with pyinstaller"
	$(CMD) pyinstaller --onefile datawagon/main.py --name datawagon --target-arch universal2

clean-env:
	@echo "Cleaning up virtual environment"
	rm -rf .venv