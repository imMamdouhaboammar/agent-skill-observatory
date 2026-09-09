# Architecture

Agent Skill Observatory separates discovery from verification so search noise never becomes catalog truth

```text
GitHub discovery queries + official seeds
                |
                v
       Candidate repositories
                |
                v
       Recursive tree inspection
                |
         real SKILL.md?
          /          \
        no            yes
        |              |
      discard          v
                bounded file fetch
                       |
          +------------+-------------+
          |            |             |
          v            v             v
      spec parser  safety scan   repo signals
          |            |             |
          +------------+-------------+
                       |
                       v
                explainable scores
                       |
                       v
              SQLAlchemy persistence
                 /               \
                v                 v
          FastAPI service     JSON / CSV export
                |                 |
                v                 v
          live dashboard      GitHub Pages
```

## Deep modules

`parser.py` owns manifest parsing and open-spec validation behind `parse_skill_directory`

`security.py` owns static safety rules behind `assess_skill_security`

`scoring.py` owns score policy behind `score_skill`

`github.py` owns GitHub API interaction and candidate discovery

`pipeline.py` owns bounded remote materialization and the repository-to-indexed-skill workflow

`repository.py` owns persistence operations and historical metric calculations

`catalog.py` owns export and aggregate catalog statistics

`api.py` exposes read-only product APIs and serves the dashboard

## Storage

SQLite is the default local store. Any SQLAlchemy PostgreSQL URL can be supplied through `SKILLOBS_DATABASE_URL` for a hosted deployment

GitHub Actions exports text artifacts to `data/catalog.json`, `data/catalog.csv`, and `data/stats.json`. The history database is cached by Actions rather than committed as a binary file

## Failure model

A repository-level fetch failure is isolated and recorded in the refresh report. It does not invalidate skills already indexed from other repositories

A malformed manifest can still be indexed with `spec.valid=false` when it can be parsed enough to preserve evidence. A manifest without usable YAML frontmatter is rejected from indexing and surfaced as a pipeline error
