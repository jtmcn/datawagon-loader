CMD:=poetry run
PYMODULE:=datawagon
ENTRYPOINT:=main.py
TESTS:=tests


help: ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

better: reset-and-update build-app install-app  ## Reset local code and update from remote, build and install app

pre-commit: check lint type format isort test  ## Run pre-commit checks

reset-and-update: ## Reset local code and update from remote
	git fetch
	git reset --hard origin/main

check:
	poetry check

run: ## Run app
	$(CMD) python $(PYMODULE)/$(ENTRYPOINT)

build-app: ## Build app
	poetry build

install-app: ## Install app
	poetry install

lint: ## Lint code
	$(CMD) flake8 $(PYMODULE) $(TESTS)

format: ## Format code
	$(CMD) black $(PYMODULE) $(TESTS)

type: ## Type check code
	$(CMD) mypy --namespace-packages --explicit-package-bases $(PYMODULE) $(TESTS)

test: ## Run tests
	$(CMD) pytest --cov=$(PYMODULE) $(TESTS)

test-cov: ## Run tests with coverage
	$(CMD) pytest --cov=$(PYMODULE) $(TESTS) --cov-report html

isort: ## Sort imports
	$(CMD) isort --recursive $(PYMODULE) $(TESTS)

build-binary: ## Build binary
	$(CMD) pyinstaller --onefile datawagon/main.py --name datawagon --target-arch universal2
