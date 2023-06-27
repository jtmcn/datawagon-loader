.PHONY: all clean lint type test test-cov

CMD:=poetry run
PYMODULE:=datawagon
ENTRYPOINT:=main.py
TESTS:=tests


run:
	$(CMD) python $(PYMODULE)/$(ENTRYPOINT)

lint:
	$(CMD) flake8 $(PYMODULE) $(TESTS)

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