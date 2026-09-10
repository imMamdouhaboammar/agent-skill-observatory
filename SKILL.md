---
name: agent-skill-observatory
version: 0.2.0
description: >
  Evidence-based discovery, specification validation, static security analysis, and
  multi-dimensional scoring for open Agent Skills across GitHub and local workspaces.
  Use when an agent needs to evaluate a skill before installation, scan a local skill
  directory for malicious or risky instructions, audit specification compliance, or
  inspect catalog evidence across Claude Code, Codex, Antigravity, Cursor, OpenCode,
  and Skills.sh.
  DO NOT USE for executing unvetted third-party skill code or general non-skill tasks.
author: Mamdouh Aboammar <mamdouhfces1997@gmail.com>
license: Apache-2.0
homepage: https://imMamdouhaboammar.github.io/agent-skill-observatory/
repository: https://github.com/imMamdouhaboammar/agent-skill-observatory
hosts:
  - antigravity
  - claude
  - cursor
  - codex
  - opencode
  - skills-sh
---

<!-- Copyright (c) 2026 Mamdouh Aboammar. Licensed under Apache-2.0. -->

# Agent Skill Observatory

Evaluate, audit, score, and discover AI Agent Skills using strict static analysis and
evidence-based metrics — **without executing untrusted code.**

---

## Host Contract Table

| Host | Discovery path | Shell available | Tested |
|---|---|---|---|
| Antigravity / Gemini CLI | `.agents/skills/agent-skill-observatory/SKILL.md` | Yes | ✅ |
| Claude Code | `SKILL.md` (root) + `marketplace.json` | Yes | ✅ |
| Cursor | `.agents/skills/agent-skill-observatory/SKILL.md` | Limited | ✅ |
| Codex | `.agents/skills/agent-skill-observatory/SKILL.md` | Yes | ✅ |
| OpenCode | `SKILL.md` via `skill.package.json` | Yes | ✅ |
| Skills.sh | `SKILL.md` via `.skills.json` | Yes | ✅ |

---

## Trigger Evals (BinEval Gate)

The skill MUST be loaded for these prompts:

| # | Prompt | Must load |
|---|---|---|
| T1 | "scan this local skill directory for security issues" | ✅ Yes |
| T2 | "index new Agent Skills from GitHub" | ✅ Yes |
| T3 | "what is the quality score for this skill?" | ✅ Yes |
| T4 | "audit my local skill before installing" | ✅ Yes |

The skill MUST NOT load for these prompts:

| # | Prompt | Must load |
|---|---|---|
| N1 | "write a Python function for sorting" | ❌ No |
| N2 | "check my git status" | ❌ No |
| N3 | "how do I install npm packages" | ❌ No |

---

## Non-Negotiable Invariants

1. **Zero-execution**: Never execute third-party scripts, binaries, or curl-pipe-bash installers during indexing or analysis.
2. **Provenance**: Every indexed skill points back to repository URL, branch, path, and discovery source.
3. **Multi-Dimensional Scoring**: Quality, Security, Maintenance, and Adoption scores remain separate and explainable.
4. **Manifest Grounding**: A real `SKILL.md` manifest file is required before indexing — repo name is candidate evidence only.
5. **Token Safety**: GitHub tokens are accepted only via environment — never logged, printed, or stored in catalog records.

---

## Capabilities & Workflows

### 1. Scan Local Skill Directory Before Installing

Audit a candidate skill directory for structural validity, resource inventory, and static security risks:

```bash
skillobs scan-local /path/to/candidate-skill
```

Expected output:
```json
{
  "name": "candidate-skill",
  "spec": { "valid": true, "errors": [], "warnings": [] },
  "security": { "score": 100, "findings": [] },
  "score": {
    "overall": 82,
    "quality": 85,
    "security": 100,
    "maintenance": 90,
    "adoption": 45
  },
  "resources": { "scripts": 1, "references": 2, "assets": 0, "other": 0 }
}
```

### 2. Inspect Catalog Evidence

Query the verified index via the local or remote API:

```bash
# Query skills matching a capability or keyword with score >= 70
curl -s "http://127.0.0.1:8000/api/v1/skills?q=security&min_score=70&spec_valid=true&limit=10"
```

Or read the static catalog snapshot directly:
- `data/catalog.json`: Full skill-level records with security findings and provenance.
- `data/stats.json`: Aggregate metrics across indexed repositories and skills.
- `https://imMamdouhaboammar.github.io/agent-skill-observatory/catalog.json`: Live public catalog.

### 3. Check System Health & Security Model

```bash
skillobs doctor
```

### 4. Refresh GitHub Catalog (Safe Discovery)

```bash
# Discovers and indexes skills from GitHub trees — no remote code executed
skillobs refresh
```

### 5. Build Static Catalog & Dashboard for GitHub Pages

```bash
skillobs build-site --output-dir site
```

### 6. Serve Live API (FastAPI)

```bash
skillobs serve
# Opens http://127.0.0.1:8000 — API at /api/v1/skills, /api/v1/stats
```

---

## Security Flags Detected

The observatory scanner identifies high-risk instruction and script patterns including:

| Flag | Pattern | Severity |
|---|---|---|
| `pipe-to-shell` | Remote downloads piped into bash/sh (`curl ... \| sh`) | HIGH |
| `recursive-delete` | Forced recursive deletion (`rm -rf /`, `rm -rf ~`) | HIGH |
| `credential-access` | SSH keys (`~/.ssh`), cloud tokens (`~/.aws/credentials`), GitHub tokens | HIGH |
| `world-writable` | Insecure permissions (`chmod 777`) | MEDIUM |
| `dynamic-exec` | String evaluation (`eval()`, `exec()`) | MEDIUM |
| `privilege-escalation` | Uncontrolled root access (`sudo`) | MEDIUM |

**A high security score does not prove a skill is safe.** Always review third-party instructions and scripts before execution.

---

## Acceptance Gate

Before marking this skill as distributed on any host, verify:

- [ ] Host discovery loads this SKILL.md via the mechanism listed in the host contract table
- [ ] `skillobs scan-local` runs without error in the host environment
- [ ] Trigger prompts T1–T4 activate the skill; negative prompts N1–N3 do not
- [ ] No absolute personal paths appear in any output
- [ ] No secret-shaped content in manifest files or catalog exports

---

## References

- [Architecture Guide](docs/architecture.md) — system design and pipeline
- [Scoring Model](docs/scoring.md) — calibration tables and formula pseudocode
- [Security Model](docs/security-model.md) — threat model and zero-execution rationale
- [OmniSkill Integration](docs/omni-skill-integration.md) — host profiles and routing DAG
- [Skill Contract](references/skill-contract.md) — scoring weights and schema specification
- [Live Catalog](https://imMamdouhaboammar.github.io/agent-skill-observatory/) — GitHub Pages app
