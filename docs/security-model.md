# Security model

The index treats every third-party skill as untrusted input

## Hard rule

The crawler never executes bundled scripts, shell commands, package installers, or instructions from an indexed skill

## What the scanner does

It reads bounded text files and searches for high-impact patterns that deserve human review. Examples include remote content piped to a shell, forced recursive deletion, credential-path references, elevated privileges, dynamic code execution, and world-writable permissions

## What the scanner does not prove

A high security score does not prove a skill is safe. Static pattern matching cannot reliably identify every harmful behavior, indirect instruction, dependency risk, or social-engineering path

A low security score does not prove malicious intent. Some legitimate development skills need privileged or destructive operations

## Trust boundaries

- GitHub API responses are untrusted external data
- repository paths are validated before local materialization
- file count and size are bounded
- tokens are accepted only through environment configuration
- authorization headers and tokens must never be logged
- the public API is read-only in this release

## Reporting a vulnerability

Do not open a public issue for a vulnerability in the Observatory itself. Follow `SECURITY.md`
