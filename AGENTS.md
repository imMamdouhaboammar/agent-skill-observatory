# Agent instructions

Read `CONTEXT.md`, `docs/architecture.md`, `docs/scoring.md`, and `docs/security-model.md` before changing discovery, scoring, parsing, or safety behavior.

Non-negotiable rules:

1. Never execute scripts or commands from indexed third-party skills during discovery or analysis.
2. Preserve provenance. Every indexed skill must point back to repository, path, branch, and discovery source.
3. A repository name is candidate evidence only. A real manifest file is required before indexing a skill.
4. Keep quality, security, maintenance, and adoption scores separate. Do not collapse evidence into an unexplained popularity rank.
5. Add or update tests for behavior changes. Run `make verify` before claiming completion.
6. Never log GitHub tokens or authorization headers.
7. Do not weaken file-count, file-size, or path-traversal protections without a documented security review.
