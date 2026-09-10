# check-content-alignment

Source repository: [707734712/agents-in-sdlc](https://github.com/707734712/agents-in-sdlc)

Canonical key: `707734712/agents-in-sdlc:.github/skills/check-content-alignment`

Manifest: [https://github.com/707734712/agents-in-sdlc/blob/main/.github/skills/check-content-alignment/SKILL.md](https://github.com/707734712/agents-in-sdlc/blob/main/.github/skills/check-content-alignment/SKILL.md)

## Description

Find workshop lessons that should change alongside an edit. Scans a diff (staged, unstaged, or a branch range) of the Copilot Workshops docs, extracts what changed, then searches the rest of docs/** for duplicated or parallel passages that now risk drifting out of sync — prose that used to be a shared partial and is now copied across pages, the same concept taught across the VS Code / CLI / App / Cloud harnesses, and cross-references to the changed page. Use after editing lesson content under docs/, before committing or opening a PR, or whenever asked to "check content alignment", "find related content to update", "what else should change", or "check for drift". Reports candidate files with line ranges and rationale; it does NOT edit content.

## Classification

Categories: content, design, engineering, productivity
Client compatibility: GitHub Copilot
License: MIT

## Resources

Scripts: 0
References: 0
Assets: 0
Other: 0

## Scores

Overall: 84
Quality: 85
Security: 100
Maintenance: 100
Adoption: 10

## Static security findings

No static findings recorded

Static analysis is not malware certification

## Publication metadata

First seen: unknown
Indexed: 2026-09-09T20:55:16.707066+00:00
Published: 2026-09-10T13:44:22.631048+00:00
Publication event: add
Source fingerprint: ``
Analysis fingerprint: ``
