# agent-orchestration

Published Skills: 1

| Skill | Repository | Score | Security | Stars | Description |
|---|---|---:|---:|---:|---|
| [gh-pr-review](../skills/CherryHQ/cherry-studio/.agents/skills/gh-pr-review/README.md) | [CherryHQ/cherry-studio](https://github.com/CherryHQ/cherry-studio) | 100 | 100 | 51666 | Automated Cherry Studio review for local branches, PRs, commits, files, architecture docs, and repository skills. Use for code or documentation reviews that need project-specific naming, main/renderer/shared placement and dependency rules, IpcApi and DataApi boundaries, lifecycle/service ownership, renderer hooks, React/UI conventions, and tests. Review depth adapts to diff size and runtime subagent capability (single-agent or multi-agent reviewer-verifier). Report-only by default; code fixes and GitHub submission each require explicit invocation-time authorization (`fix` / `submit`). Normal-review prompts and safe interruption behavior follow the interaction contract below. To diagnose gaps in the skill after a review session, run `/gh-pr-review diag`. |
