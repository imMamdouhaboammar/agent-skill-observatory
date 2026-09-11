# breaking-change

Source repository: [alpha-omega-security/scrutineer](https://github.com/alpha-omega-security/scrutineer)

Canonical key: `alpha-omega-security/scrutineer:skills/breaking-change`

Manifest: [https://github.com/alpha-omega-security/scrutineer/blob/main/skills/breaking-change/SKILL.md](https://github.com/alpha-omega-security/scrutineer/blob/main/skills/breaking-change/SKILL.md)

## Description

Decide whether a finding's suggested fix is a breaking change for top dependents. Reads the unified-diff fix on the finding, identifies the public API surface that changes (signatures, exports, removed fields, renamed types), and lists which top dependents are most likely to break. Static analysis on the diff and the dependent metadata from the scrutineer API; never executes dependent code.

## Classification

Categories: content, data, documentation, engineering, testing
Client compatibility: not explicitly detected
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
Source fingerprint: `5638ced5eac50e8cec481b9e0d3f5f5d793e70b2506be7e0726d62305c2ed427`
Analysis fingerprint: `a1c2314b0f3cb64bbe374e999307e938cdf5212327b5822e1537f276b47a00b0`
