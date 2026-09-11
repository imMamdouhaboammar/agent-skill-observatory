# advisory-deep-dive

Source repository: [alpha-omega-security/scrutineer](https://github.com/alpha-omega-security/scrutineer)

Canonical key: `alpha-omega-security/scrutineer:skills/advisory-deep-dive`

Manifest: [https://github.com/alpha-omega-security/scrutineer/blob/main/skills/advisory-deep-dive/SKILL.md](https://github.com/alpha-omega-security/scrutineer/blob/main/skills/advisory-deep-dive/SKILL.md)

## Description

Re-audit every past GHSA/CVE advisory published against this repository, anchored on each advisory's fix commit, for four failure modes, a regression of the original bug, a bypass of the fix, an incomplete fix that left a path open, and the same class of bug in sibling code the fix never touched. Records one verdict per advisory (fixed, bypass, variant or regressed) with standalone evidence, opening findings for anything that did not hold, and a fixed verdict backs a public fix-audit certificate. Use when you want to prove that prior fixes actually held rather than trusting that a shipped patch closed the hole. The target is this codebase's own first-party source, not its dependencies.

## Classification

Categories: agent-orchestration, commerce, engineering, research, security, testing
Client compatibility: Claude Code
License: MIT

## Resources

Scripts: 0
References: 0
Assets: 0
Other: 1

## Scores

Overall: 100
Quality: 100
Security: 100
Maintenance: 100
Adoption: 74

## Static security findings

No static findings recorded

Static analysis is not malware certification

## Publication metadata

First seen: unknown
Indexed: 2026-09-11T23:36:10.775186+00:00
Published: 2026-09-11T23:41:04.105755+00:00
Publication event: add
Source fingerprint: `d38b33c43309fd67ddbad73c9b2537b5070685867540e315eb7553e5bee7d912`
Analysis fingerprint: `4d7499b5e28199f66ac3b66203e1a367c75302d2e09022c803f7b8f25a3f70ea`
