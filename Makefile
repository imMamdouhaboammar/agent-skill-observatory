.PHONY: install test lint typecheck migration-check verify serve refresh site clean

install:
	python -m pip install -e '.[dev]'

test:
	python -m pytest --cov=skill_observatory --cov-report=term-missing --cov-fail-under=80

lint:
	python -m ruff check .

typecheck:
	python -m mypy src

migration-check:
	rm -f migration-check.db
	SKILLOBS_DATABASE_URL=sqlite+pysqlite:///./migration-check.db skillobs migrate
	SKILLOBS_DATABASE_URL=sqlite+pysqlite:///./migration-check.db alembic check
	rm -f migration-check.db

verify: lint typecheck migration-check test

serve:
	skillobs serve --host 0.0.0.0 --port 8000

refresh:
	skillobs refresh

site:
	skillobs build-site --output-dir site

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov site dist build
	rm -f .coverage migration-check.db
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
