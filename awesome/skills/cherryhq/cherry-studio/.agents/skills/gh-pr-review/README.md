# gh-pr-review

Source repository: [CherryHQ/cherry-studio](https://github.com/CherryHQ/cherry-studio)

Canonical key: `cherryhq/cherry-studio:.agents/skills/gh-pr-review`

Manifest: [https://github.com/CherryHQ/cherry-studio/blob/main/.agents/skills/gh-pr-review/SKILL.md](https://github.com/CherryHQ/cherry-studio/blob/main/.agents/skills/gh-pr-review/SKILL.md)

## Description

Automated Cherry Studio review for local branches, PRs, commits, files, architecture docs, and repository skills. Use for code or documentation reviews that need project-specific naming, main/renderer/shared placement and dependency rules, IpcApi and DataApi boundaries, lifecycle/service ownership, renderer hooks, React/UI conventions, and tests. Review depth adapts to diff size and runtime subagent capability (single-agent or multi-agent reviewer-verifier). Report-only by default; code fixes and GitHub submission each require explicit invocation-time authorization (`fix` / `submit`). Normal-review prompts and safe interruption behavior follow the interaction contract below. To diagnose gaps in the skill after a review session, run `/gh-pr-review diag`.

## Classification

Categories: agent-orchestration, commerce, design, documentation, engineering, productivity
Client compatibility: GitHub Copilot, OpenAI Codex
License: AGPL-3.0

## Resources

Scripts: 0
References: 10
Assets: 0
Other: 1

## Scores

Overall: 100
Quality: 93
Security: 100
Maintenance: 100
Adoption: 80

## Static security findings

No static findings recorded

Static analysis is not malware certification

## Publication metadata

First seen: unknown
Indexed: 2026-09-11T08:05:17.684097+00:00
Published: 2026-09-11T08:07:15.832049+00:00
Publication event: add
Source fingerprint: `bb19b5fa99ef13b7b5e5f535b0fe33bd2c0c7b25d3fa2e7cd70865e85e705e92`
Analysis fingerprint: `db69c978821caf08af65be786096af0a56490c32c365e1aa9f4e4ca521d594bb`
