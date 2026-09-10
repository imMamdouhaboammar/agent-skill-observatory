.PHONY: install test lint typecheck migration-check verify serve refresh publish site clean

VENV ?= $(shell if [ -f .venv/bin/python ]; then echo .venv/bin/; fi)
PYTHON ?= $(VENV)python
RUFF ?= $(VENV)ruff
MYPY ?= $(VENV)mypy
PYTEST ?= $(VENV)pytest
ALEMBIC ?= $(VENV)alembic
SKILLOBS ?= $(VENV)skillobs

install:
	$(PYTHON) -m pip install -e '.[dev]'

test:
	$(PYTHON) -m pytest --cov=skill_observatory --cov-report=term-missing --cov-fail-under=80

lint:
	$(RUFF) check .

typecheck:
	$(MYPY) src

migration-check:
	rm -f migration-check.db
	SKILLOBS_DATABASE_URL=sqlite+pysqlite:///./migration-check.db $(SKILLOBS) migrate
	SKILLOBS_DATABASE_URL=sqlite+pysqlite:///./migration-check.db $(ALEMBIC) check
	rm -f migration-check.db

verify: lint typecheck migration-check test

serve:
	$(SKILLOBS) serve --host 0.0.0.0 --port 8000

refresh:
	$(SKILLOBS) refresh

publish:
	skillobs publish

site:
	$(SKILLOBS) build-site --output-dir site

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov site dist build
	rm -f .coverage migration-check.db
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
