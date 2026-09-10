# Security Policy

<!-- Copyright (c) 2026 Mamdouh Aboammar. Licensed under Apache-2.0. -->

## Supported Versions

Security fixes are applied to the latest released version.

| Version | Supported |
|---|---|
| 0.2.x (current) | ✅ Active |
| 0.1.x | ⚠️ Critical fixes only |
| < 0.1 | ❌ End of life |

## Private Disclosure

**Do not open a public GitHub issue for a security vulnerability.**

Report vulnerabilities privately via one of these channels:

1. **GitHub Security Advisories** (preferred): Navigate to
   `https://github.com/imMamdouhaboammar/agent-skill-observatory/security/advisories/new`
2. **Email**: [mamdouhfces1997@gmail.com](mailto:mamdouhfces1997@gmail.com)
   — use subject line `[SECURITY] agent-skill-observatory — <brief description>`

Do not include tokens, private repository content, credentials, or working exploit payloads in
any initial report.

## Disclosure Timeline

| Day | Action |
|---|---|
| 0 | Report received; acknowledgement within 48 hours |
| 1–7 | Triage, reproduction, and severity classification |
| 7–21 | Fix development and private validation |
| 21–30 | Coordinated public disclosure and patch release |
| 30+ | CVE publication if severity ≥ HIGH |

## Scope

High-priority reports include:

- Remote code execution caused by indexing a repository
- Path traversal during remote materialization
- GitHub token disclosure through logs, exports, or API responses
- Unsafe parsing that writes outside the temporary skill directory
- Public API behavior that mutates catalog or host state unexpectedly
- Workflow changes that execute indexed third-party scripts
- Supply-chain compromise via unpinned GitHub Action SHAs

Out of scope:

- Disagreement with a skill's security score — scores are static analysis signals, not guarantees
- Theoretical vulnerabilities without a proof-of-concept or reproduction path
- Vulnerabilities in GitHub Actions infrastructure outside this repository's control

## Security Controls

See [`docs/security-model.md`](docs/security-model.md) for the full threat model.
