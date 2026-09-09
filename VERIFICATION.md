# Verification Record

Verification date: 2026-09-09

This file records what was executed against the source tree before the v0.1.0 handoff.

## Passed locally

- `pytest` full suite: 23 passed
- Coverage: 85.96%, above the repository gate of 80%
- `compileall` for `src/` and `tests/`
- YAML parsing for every workflow in `.github/workflows/`
- Alembic upgrade from an empty SQLite database to `head`
- `alembic check`: no new upgrade operations detected
- `skillobs scan-local` against a valid local fixture
- FastAPI health, stats, skill-list, root UI, JavaScript, and CSS smoke requests
- Static site generation with `catalog.json` and `stats.json`
- Wheel build with local build dependencies
- Wheel installation into a clean target directory
- Packaged web assets present after wheel installation
- Packaged Alembic assets present after wheel installation
- Database migration executed from the installed wheel

## Configured in CI but not executed locally

The execution environment used for this handoff did not have Ruff or mypy installed, and outbound package installation was unavailable. The CI workflow installs the development extras and runs both checks on Python 3.11, 3.12, and 3.13.

Docker was not available in the handoff environment. The Dockerfile uses a non-root user, applies Alembic migrations before serving, and includes an HTTP healthcheck.

## Security boundary

No third-party skill scripts were executed during verification. Local and remote skill analysis is static by design.
