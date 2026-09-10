# Architecture

<!-- Copyright (c) 2026 Mamdouh Aboammar. Licensed under Apache-2.0. -->

Agent Skill Observatory separates discovery from verification so search noise never becomes catalog truth.

## Pipeline Overview

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
                 bounded file fetch (≤ 250 KB)
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
                 (quality/security/maintenance/adoption)
                        |
                        v
               SQLAlchemy persistence
                  /               \
                 v                 v
           FastAPI service     JSON / CSV export
                 |                 |\
                 v                 v  v
           live dashboard    GitHub Pages  llms.txt
```

## Multi-Agent Standard (OmniSkill Integration)

As of v0.2.0, Agent Skill Observatory adheres to the OmniSkill universal routing standard.
The skill artifact (`SKILL.md` + `skill.package.json`) is distributed to all major agent hosts
via a host-contract DAG:

```text
Intent (Any Agent Host)
   ↓
   OmniSkill Dynamic Router
   ↓ classifies host capability contract
   ↓
   Execution DAG
   ├── Antigravity / Gemini CLI  → .agents/skills/
   ├── Claude Code               → .claude/skills/ + marketplace.json
   ├── Cursor                    → .agents/skills/
   ├── Codex                     → .agents/skills/ + plugin.json
   ├── OpenCode                  → skill.package.json
   └── Skills.sh                 → .skills.json
   ↓
   BinEval Gate (discovery + behavior + portability)
   ↓
   Release (all hosts)
```

See [`docs/omni-skill-integration.md`](./omni-skill-integration.md) for the full host profile table,
trigger eval examples, and packaging reference.

## Core Modules

| Module | Responsibility |
|---|---|
| `parser.py` | Manifest parsing and open-spec validation (`parse_skill_directory`) |
| `security.py` | Static safety rules (`assess_skill_security`) |
| `scoring.py` | Score policy (`score_skill`) |
| `github.py` | GitHub API interaction and candidate discovery |
| `pipeline.py` | Bounded remote materialization, repository→indexed-skill workflow |
| `repository.py` | Persistence operations and historical metric calculations |
| `catalog.py` | Export and aggregate catalog statistics |
| `api.py` | Read-only product APIs and dashboard serving |

## Storage

SQLite is the default local store. Any SQLAlchemy PostgreSQL URL can be supplied through
`SKILLOBS_DATABASE_URL` for a hosted deployment.

GitHub Actions exports text artifacts to `data/catalog.json`, `data/catalog.csv`, and
`data/stats.json`. The history database is cached by Actions rather than committed as a binary.

## Failure Model

A repository-level fetch failure is isolated and recorded in the refresh report.
It does not invalidate skills already indexed from other repositories.

A malformed manifest can still be indexed with `spec.valid=false` when it can be parsed enough to
preserve evidence. A manifest without usable YAML frontmatter is rejected from indexing and surfaced
as a pipeline error.
