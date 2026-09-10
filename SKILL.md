---
name: agent-skill-observatory
description: >
  Evidence-based discovery, specification validation, static security analysis, and multi-dimensional
  scoring for open Agent Skills across GitHub and local workspaces. Use when an agent needs to evaluate
  a skill before installation, scan a local skill directory for malicious or risky instructions, audit
  specification compliance, or inspect catalog evidence across Claude Code, Codex, Antigravity, and Cursor.
  DO NOT USE for executing unvetted third-party skill code or general non-skill tasks.
---

# Agent Skill Observatory

Evaluate, audit, score, and discover AI Agent Skills using strict static analysis and evidence-based metrics without executing untrusted code.

## Invariants

1. **Static Analysis Only**: Never execute third-party scripts, binary binaries, or curl-pipe-bash installers during indexing or analysis.
2. **Provenance Preservation**: Every indexed skill points back to its repository URL, branch, path, and discovery source.
3. **Multi-Dimensional Scoring**: Quality, Security, Maintenance, and Adoption scores remain separate and explainable. Never collapse into an unexplained vanity metric.
4. **Manifest Grounding**: A candidate repository requires a verified `SKILL.md` manifest before being recognized as a skill.

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

### 3. Check System Health & Security Model
```bash
skillobs doctor
```

### 4. Build Static Catalog & Dashboard
Export static JSON/CSV artifacts and compile the browser-ready catalog:
```bash
skillobs build-site --output-dir site
```

---

## Security Flags Detected

The observatory scanner identifies high-risk instruction and script patterns including:
- **`pipe-to-shell`**: Remote script downloads piped directly into bash/sh (`curl ... | sh`).
- **`recursive-delete`**: Forced recursive deletion commands (`rm -rf /`, `rm -rf ~`).
- **`credential-access`**: References to SSH keys (`~/.ssh`), cloud tokens (`~/.aws/credentials`), or GitHub tokens.
- **`world-writable`**: Insecure permission changes (`chmod 777`).
- **`dynamic-exec`**: Dynamic string evaluation in code (`eval()`, `exec()`).
- **`privilege-escalation`**: Uncontrolled root privilege requests (`sudo`).

Refer to `references/skill-contract.md` for complete scoring weights and schema specifications.
