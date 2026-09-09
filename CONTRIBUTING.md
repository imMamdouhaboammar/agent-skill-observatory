# Contributing

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
make verify
```

## Change rules

Read `CONTEXT.md` and the relevant ADR before changing discovery, parsing, scoring, or security behavior

Behavior changes need tests at the public module seam

Do not add a crawler path that executes third-party code

Do not turn a repository naming convention into catalog truth without source evidence

Do not hide component scores behind a new opaque overall metric

## Pull requests

A useful pull request states:

- problem and evidence
- changed behavior
- tests added or changed
- security implications
- data or schema implications
- verification commands and results

Run `make verify` before opening the pull request
