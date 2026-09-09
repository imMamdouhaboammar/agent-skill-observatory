# Security policy

## Supported versions

Security fixes are applied to the latest released minor version

## Reporting

Please report vulnerabilities privately through GitHub Security Advisories for the repository that hosts your deployment

Do not include tokens, private repository content, credentials, or exploit payloads in public issues

## Scope

High-priority reports include:

- remote code execution caused by indexing a repository
- path traversal during remote materialization
- GitHub token disclosure
- unsafe parsing that writes outside the temporary skill directory
- public API behavior that mutates catalog or host state unexpectedly
- workflow changes that execute indexed third-party scripts

The static safety score is explicitly not a malware guarantee and disagreement with a score alone is not a security vulnerability in the Observatory
