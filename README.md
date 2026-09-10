# Agent Skill Observatory

A real discovery, validation, safety-review, ranking, and publishing product for the open Agent Skills ecosystem

It is designed to answer a more useful question than “which GitHub repositories have `skills` in the name?”

> Which repositories contain actual Agent Skills, what evidence supports each one, how closely does each manifest follow the open format, what static safety concerns are visible, how maintained is the source, and why is it ranked where it is?

## What makes it different

- Requires an actual `SKILL.md` before a skill is indexed
- Validates required Agent Skills metadata instead of trusting repository names
- Preserves repository, branch, path, discovery query, and manifest provenance
- Separates quality, security, maintenance, and adoption scores
- Detects duplicated manifests by normalized content fingerprint
- Infers client compatibility only when there is evidence in paths, metadata, or files
- Classifies useful categories for browsing without an external AI dependency
- Stores historical repository snapshots so momentum can be measured over time
- Never executes third-party skill scripts during indexing
- Runs as a FastAPI product or as a GitHub-native static catalog with Actions + Pages
- Exports JSON and CSV for researchers, agents, dashboards, and downstream tools

## Awesome directory on GitHub

The catalog is published directly inside this repository, not only through a hosted UI

- [`AWESOME.md`](./AWESOME.md) is the complete generated directory of verified Agent Skills and repositories
- [`awesome/README.md`](./awesome/README.md) is the same catalog exposed as a dedicated GitHub path
- [`data/catalog.json`](./data/catalog.json) contains skill-level evidence
- [`data/repositories.json`](./data/repositories.json) contains repository-level rollups

The refresh workflow checks GitHub every 15 minutes and regenerates the Markdown directory, root README summary, JSON/CSV exports and statistics when it runs

## Live Awesome Index

<!-- AWESOME_INDEX_START -->
Catalog has not been refreshed yet
<!-- AWESOME_INDEX_END -->

## Standards grounding

The parser follows the open Agent Skills format documented at `https://agentskills.io/specification`

A skill is expected to contain a `SKILL.md` with YAML frontmatter including `name` and `description`, plus optional supporting directories such as `scripts/`, `references/`, and `assets/`

Client-specific evidence is kept separate from open-format validity. For example, OpenAI Codex can discover repository skills under `.agents/skills`, while GitHub Copilot documents project skill locations including `.github/skills`, `.claude/skills`, and `.agents/skills`

## Architecture

```text
GitHub candidate discovery
  repo search + authenticated code search + official seeds
                     |
                     v
             repository tree
                     |
              real SKILL.md?
              /          \
            no            yes
            |              |
          ignore      bounded fetch
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
   spec validation    static safety      repo evidence
        |                  |                  |
        +------------------+------------------+
                           |
                           v
                 explainable scoring
                           |
                           v
                SQLite / PostgreSQL
                   /              \
                  v                v
             FastAPI + UI      JSON / CSV
                                  |
                                  v
                             GitHub Pages
```

More detail is in `docs/architecture.md`

## Quick start

Requires Python 3.11+

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

A GitHub token is optional for local parsing and anonymous API use, but recommended for real catalog refreshes and required for the additional GitHub Code Search discovery path

```bash
export SKILLOBS_GITHUB_TOKEN=github_token_here
skillobs refresh --max-repositories 50
skillobs serve
```

Open `http://127.0.0.1:8000`

API docs are available at `http://127.0.0.1:8000/docs`

## Scan one local skill

This is useful before installing or publishing a skill

```bash
skillobs scan-local path/to/my-skill
```

The command returns spec validation, static safety findings, component scores, and resource counts

It does not execute the skill

## CLI

```text
skillobs init-db
skillobs migrate
skillobs scan-local PATH
skillobs refresh [--max-repositories N]
skillobs export OUTPUT --format json|csv
skillobs stats [--output stats.json]
skillobs build-site --output-dir site
skillobs doctor
skillobs serve
```

## Configuration

All application settings use the `SKILLOBS_` prefix

| Variable | Default | Purpose |
|---|---|---|
| `SKILLOBS_GITHUB_TOKEN` | empty | Higher GitHub quota and authenticated code search |
| `SKILLOBS_DATABASE_URL` | `sqlite+pysqlite:///./skill_observatory.db` | SQLAlchemy database URL |
| `SKILLOBS_MAX_REPOSITORIES_PER_QUERY` | `50` | Candidate bound for each repository query |
| `SKILLOBS_REQUEST_TIMEOUT_SECONDS` | `30` | GitHub request timeout |

For production deployments run `skillobs migrate` before starting the service. `init-db` remains a local-development convenience

For PostgreSQL install the optional driver

```bash
python -m pip install -e '.[postgres]'
export SKILLOBS_DATABASE_URL='postgresql+psycopg://user:pass@host/db'
```

## Discovery strategy

The default repository queries include:

```text
topic:agent-skills
"agent skills" in:name,description,readme
"claude skills" in:name,description,readme
"codex skills" in:name,description,readme
"SKILL.md" in:readme
```

When authenticated, the crawler also uses GitHub Code Search for manifests inside common project skill paths

The candidate list is deliberately broad. A repository only becomes part of the catalog after the tree contains a real manifest

See `docs/discovery.md`

## Scoring

Every skill keeps four visible component scores

- Quality: specification evidence, description quality, instruction depth, tests/evals, README evidence
- Security: static findings from instructions and bundled text files
- Maintenance: recency and archival state
- Adoption: bounded star/fork popularity plus historical velocity when snapshots exist

The overall score currently weighs them 35 / 30 / 20 / 15 respectively

Archived repositories are capped below 50 overall so historical popularity cannot hide abandonment

See `docs/scoring.md`

## Security model

The index treats third-party skills as untrusted input

It never executes remote scripts, installers, or commands while crawling

The static scanner currently flags patterns including:

- downloaded content piped directly into a shell
- forced recursive deletion
- common credential or private-key paths
- dynamic `eval` / `exec`
- `chmod 777`
- `sudo`

This is review assistance, not malware certification. Read `docs/security-model.md` before using the score for policy decisions

## API

### Health

```http
GET /api/v1/health
```

### Catalog stats

```http
GET /api/v1/stats
```

### Skills

```http
GET /api/v1/skills?q=review&min_score=70&spec_valid=true&limit=50&offset=0
```

The service is read-only in this release

## GitHub-native mode

The repository contains Actions for:

- CI across Python 3.11, 3.12, and 3.13
- CodeQL analysis
- dependency review on pull requests
- Dependabot updates
- catalog scan and Markdown/data publication every 15 minutes
- generated `AWESOME.md`, `awesome/README.md`, README summary, JSON/CSV and repository rollup commits
- historical database caching without committing a binary DB
- GitHub Pages deployment of the static dashboard

The committed `data/` folder is intentionally text-only

## Docker

```bash
docker compose up --build
```

The container runs as a non-root user, applies Alembic migrations before startup, exposes a healthcheck, and stores its SQLite database in a named volume

## Verification

```bash
make verify
```

This runs Ruff, mypy, Alembic schema verification, pytest, and the 80% coverage gate

## Product documentation

- `CONTEXT.md`: canonical domain language
- `docs/architecture.md`: runtime and module architecture
- `docs/discovery.md`: candidate and verification policy
- `docs/scoring.md`: score policy
- `docs/security-model.md`: trust boundaries and limitations
- `docs/adr/`: architectural decisions
- `ROADMAP.md`: next product stages
- `AGENTS.md`: rules for coding agents working in this repository

## Current release boundary

This repository is a production-minded v0.1 foundation, not a claim that static analysis can determine whether any third-party skill is safe to execute

The most important future step is isolated dynamic evaluation in disposable sandboxes, kept as a separate trust domain from the primary catalog crawler

## License

Apache-2.0
