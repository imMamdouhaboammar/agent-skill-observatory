# Skill Contract & Behavioral Specification

This document defines the interface, evidence standards, and scoring invariants of the Agent Skill Observatory.

## Scoring Model Specification

The observatory calculates a composite score from four independent dimensions:

$$\text{Overall Score} = 0.35 \times Q + 0.30 \times S + 0.20 \times M + 0.15 \times A$$

Where:
- **$Q$ (Quality Score)**: Specification compliance (valid `SKILL.md` frontmatter, name format, description depth, existence of test/eval suites, and documentation).
- **$S$ (Security Score)**: Static pattern detection across instructions and bundled scripts. Base score starts at 100 and decrements on detected patterns (e.g. -25 for pipe-to-shell, -25 for credential references, -15 for chmod 777).
- **$M$ (Maintenance Score)**: Recency of repository push and archival state. Repositories archived on GitHub are capped at a maximum overall score of 50.
- **$A$ (Adoption Score)**: Bounded popularity based on stars, forks, and 7-day velocity from historical repository snapshots.

## Safety & Trust Boundaries

1. **Static Analysis Guarantee**: At no point during discovery, tree parsing, or scoring does the observatory execute third-party code.
2. **Path Sanitization**: All file paths fetched from git trees are sanitized using `PurePosixPath` and verified against directory traversal (`../`) attacks.
3. **Resource Bound Limits**:
   - Max skill files scanned: 120
   - Max single file read size: 512 KB
   - Request timeout: 30 seconds default
