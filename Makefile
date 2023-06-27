.PHONY: run setup format lint type test test-cov isort

CMD:=poetry run
PYMODULE:=datawagon
ENTRYPOINT:=main.py
TESTS:=tests


run:
	$(CMD) python $(PYMODULE)/$(ENTRYPOINT)

setup:
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

# clean:
# 	git clean -Xdf # Delete all files in .gitignore