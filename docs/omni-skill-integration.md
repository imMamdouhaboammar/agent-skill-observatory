# OmniSkill Integration

<!-- Copyright (c) 2026 Mamdouh Aboammar. Licensed under Apache-2.0. -->

Agent Skill Observatory v0.2.0 fully adheres to the OmniSkill universal multi-agent standard.
The skill artifact is distributed to all major agent platforms without vendor lock-in.

## Host-Contract Routing DAG

```text
Intent (any agent host)
   ↓
   OmniSkill Dynamic Router  ←  classifies host capability contract
   ↓
   Execution DAG
   ├── Antigravity / Gemini CLI  → .agents/skills/agent-skill-observatory/SKILL.md
   ├── Claude Code               → .claude/skills/ + marketplace.json
   ├── Cursor / Codex            → .agents/skills/ + optional plugin.json
   ├── OpenCode                  → skill.package.json
   └── Skills.sh                 → .skills.json
   ↓
   BinEval Gate (discovery + behavior + portability)
   ↓
   Release (all hosts)
```

## Host Profile Table

| Host | Discovery mechanism | Package layout | Shell available |
|---|---|---|---|
| **Antigravity / Gemini CLI** | `.agents/skills/<name>/SKILL.md` in repo | Folder drop | Yes |
| **Claude Code** | `marketplace.json` or `.claude/skills/` | Folder drop | Yes |
| **Cursor** | `.agents/skills/<name>/SKILL.md` | Folder drop | Limited |
| **Codex** | `.agents/skills/<name>/SKILL.md` + `.codex/` | Folder + plugin.json | Yes |
| **OpenCode** | `skill.package.json` registry | npm/bun package | Yes |
| **Skills.sh** | `.skills.json` manifest | registry entry | Yes |

## Trigger Evaluation (BinEval Gate)

The skill must pass three trigger checks per host before a distribution claim is made:

### Positive Triggers (must load skill)
1. "scan this local skill directory for security issues"
2. "index new Agent Skills from GitHub"
3. "what is the quality score for this skill?"

### Negative Triggers (must NOT load skill)
1. "write a Python function" — general coding, not skill-related
2. "check my git status" — devops, not skill observatory

### Portability Gate
For each host, confirm:
- [ ] Discovery loads `SKILL.md` via host mechanism
- [ ] Required file-read and search capabilities are available
- [ ] No host-specific tool names appear in universal instructions
- [ ] Package paths resolve after install

## Distribution Manifests

| File | Purpose |
|---|---|
| [`SKILL.md`](../SKILL.md) | Universal skill instructions |
| [`skill.package.json`](../skill.package.json) | OpenCode / npm-style registry entry |
| [`marketplace.json`](../marketplace.json) | Claude Code marketplace metadata |
| [`.skills.json`](../.skills.json) | Skills.sh registry entry |
| [`install.sh`](../install.sh) | Universal installer script |
| [`package.json`](../package.json) | Bun/npm package metadata |

## Evidence Rules

- Never claim trigger behavior on a host that has not been tested.
- A host-specific fix is a hypothesis for another host, not proof.
- Package paths must be validated inside the package root.
- No secret-shaped content or personal absolute paths in manifests.
