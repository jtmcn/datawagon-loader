.PHONY: run setup format lint type test test-cov isort

CMD:=poetry run
PYMODULE:=datawagon
ENTRYPOINT:=main.py
TESTS:=tests


better: reset-local-and-update-code	build-app install-app

reset-local-and-update-code: 
	git fetch
	git reset --hard origin/main

run:
	$(CMD) python $(PYMODULE)/$(ENTRYPOINT)

build-app:
	poetry build

install-app:
	poetry install

lint:
	$(CMD) flake8 $(PYMODULE) $(TESTS)

format:
	$(CMD) black $(PYMODULE) $(TESTS)

type:
	$(CMD) mypy $(PYMODULE) $(TESTS)

test:
	$(CMD) pytest --cov=$(PYMODULE) $(TESTS)

test-cov:
	$(CMD) pytest --cov=$(PYMODULE) $(TESTS) --cov-report html

isort:
	$(CMD) isort --recursive $(PYMODULE) $(TESTS)

build-binary:
	$(CMD) pyinstaller --onefile datawagon/main.py --name datawagon --target-arch universal2
