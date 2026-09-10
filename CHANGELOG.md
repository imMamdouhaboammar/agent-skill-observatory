# Changelog

All notable changes to Agent Skill Observatory are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [0.2.0] - 2026-09-10

### Added

- **OmniSkill Integration**: Full multi-agent standard compliance across Antigravity, Claude Code,
  Cursor, Codex, OpenCode, and Skills.sh with host-contract routing DAG.
- **GitHub Awesome Directory**: `AWESOME.md` and `awesome/README.md` — complete generated directory
  of verified Agent Skills, auto-refreshed every 15 minutes.
- **Repository rollup tables**: Category-grouped skill tables generated from verified catalog evidence.
- **Live dashboard improvements**: Client-compatibility filter chips, one-click copy of local scan
  commands, keyboard accessibility (Escape closes modal), dark-mode support.
- **AI-Readable Endpoints**: `llms.txt` and `llms-full.txt` updated with richer v0.2.0 context.
- **JSON-LD structured data**: `SoftwareApplication` schema in GitHub Pages for Google rich results.
- **`NOTICE` file**: Standard Apache-2.0 NOTICE with Mamdouh Aboammar copyright attribution.
- **`.well-known/security.txt`**: RFC 9116 security contact file.
- **OmniSkill docs**: `docs/omni-skill-integration.md` — host profiles, routing DAG, distribution.
- **SBOM generation**: Release workflow now produces checksums and package list alongside artifacts.
- **Release checksums**: `SHA256SUMS.txt` generated and attached to GitHub Releases.

### Changed

- Catalog scan and publication cadence moved to every 15 minutes.
- GitHub Pages deployment chains from completed refresh workflows.
- `SECURITY.md` expanded with supported versions table and CVE disclosure timeline.
- CI workflows: GitHub Actions pins updated to full SHA digests for supply-chain hardening.
- `skill.package.json`, `marketplace.json`, `.skills.json` updated to version 0.2.0.
- Immediate refresh trigger added for relevant main-branch product changes.

### Fixed

- `robots.txt` now includes explicit `Sitemap:` directive.
- `sitemap.xml` `lastmod` updated to reflect current release date.

---

## [0.1.0] - 2026-09-09

### Added

- Evidence-gated GitHub discovery and real `SKILL.md` inspection.
- Open Agent Skills manifest validation.
- Bounded remote file materialization with path and size controls.
- Static safety analysis without third-party code execution.
- Explainable quality, security, maintenance, adoption, and overall scoring.
- Historical repository snapshots and star-velocity support.
- Duplicate manifest fingerprints via normalized SHA-256.
- Category classification and client compatibility evidence.
- SQLite/PostgreSQL persistence, FastAPI service, Typer CLI, static dashboard, JSON and CSV exports.
- CI, CodeQL, dependency review, Dependabot, scheduled refresh, cache-backed history, and GitHub Pages.
