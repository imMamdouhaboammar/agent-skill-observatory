# Security Model

<!-- Copyright (c) 2026 Mamdouh Aboammar. Licensed under Apache-2.0. -->

The index treats every third-party skill as untrusted input.

## Zero-Execution Invariant

**The crawler never executes bundled scripts, shell commands, package installers, or instructions
from an indexed skill.** This invariant is unconditional and cannot be relaxed by user configuration.

Rationale: a compromised or malicious skill can contain any instruction that an agent would follow.
Executing those instructions during an automated index run would turn the Observatory into an
uncontrolled remote-code execution surface. Static inspection intentionally limits what can be
inferred, but it is the only safe approach for untrusted third-party input.

## Threat Model

| Threat | Mitigation |
|---|---|
| Malicious manifest with shell injection | Zero-execution; all content treated as text |
| Path traversal via repository paths | Path sanitized before local materialization |
| Denial of service via large files | File size bounded at 250 KB; tree depth bounded |
| Token/credential exfiltration | Tokens accepted only via env; never logged or stored in DB |
| Supply-chain: compromised GitHub Action | Actions pinned to full SHA digests in CI workflows |
| Information disclosure via API | Public API is read-only; no secrets in catalog records |
| Fork-storm catalog pollution | SHA-256 fingerprint deduplication across identical manifests |
| Schema drift on DB upgrade | Alembic-controlled migrations; version checked in CI |

## What the Scanner Does

It reads bounded text files and searches for high-impact patterns that deserve human review:

- Remote content piped to a shell (`curl | bash`)
- Forced recursive deletion (`rm -rf`)
- Hardcoded credential-path references
- Dynamic code execution (`eval`, `exec`)
- World-writable permissions (`chmod 777`)
- Elevated privilege requests (`sudo`)

## What the Scanner Does Not Prove

A **high** security score does not prove a skill is safe. Static pattern matching cannot reliably
identify every harmful behavior, indirect instruction, dependency risk, or social-engineering path.

A **low** security score does not prove malicious intent. Some legitimate development skills need
privileged or destructive operations and will flag true positives.

## Trust Boundaries

- GitHub API responses are untrusted external data
- Repository paths are validated before local materialization
- File count and size are bounded
- Tokens are accepted only through environment configuration
- Authorization headers and tokens must never be logged
- The public API is read-only in this release

## Reporting a Vulnerability

Do not open a public issue for a vulnerability in the Observatory itself.
Follow `SECURITY.md` for private disclosure.
