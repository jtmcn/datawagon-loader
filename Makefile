.PHONY: setup format check test

PYTHON_VERSIONS := 3.9 3.10 3.11

setup:
	@for py in $(PYTHON_VERSIONS); do \
		pdm use -f python$$py; \
		pdm install; \
	done

format:
	pdm run duty format

check:
	pdm run duty check

test:
	@for py in $(PYTHON_VERSIONS); do \
		pdm use -f python$$py; \
		pdm run duty test; \
	done