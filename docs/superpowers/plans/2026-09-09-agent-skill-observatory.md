# Agent Skill Observatory Implementation Plan

> For agentic workers: execute each task with tests and verification before claiming completion

**Goal:** Build a real Agent Skills discovery and review product that verifies repository contents, preserves provenance, exposes explainable scoring, and can run as either a service or GitHub-native catalog

**Architecture:** Broad GitHub discovery feeds a bounded repository inspector. Real manifests are parsed and statically assessed, repository evidence is scored and persisted, then exposed through API, CLI, JSON/CSV, and a static dashboard

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic 2, HTTPX, Typer, pytest, Ruff, mypy, GitHub Actions

**Spec:** `docs/architecture.md`, `CONTEXT.md`, and ADRs in `docs/adr/`

## Global Constraints

- Never execute third-party skill scripts during indexing
- A real manifest file is required before a skill is indexed
- Preserve repository, branch, path, discovery source, and manifest evidence
- Keep quality, security, maintenance, and adoption dimensions visible
- Bound remote file count and file size
- Support SQLite locally and PostgreSQL through SQLAlchemy URLs
- Support a static GitHub Pages catalog without requiring a hosted backend

## Completed implementation slices

- [x] Manifest parser and open-spec validation
- [x] Static safety analysis
- [x] Explainable scoring
- [x] Persistence and historical repository snapshots
- [x] GitHub candidate discovery and bounded repository inspection
- [x] End-to-end indexing test
- [x] FastAPI read API
- [x] Typer CLI
- [x] Static/live dashboard
- [x] JSON/CSV exports
- [x] CI, CodeQL, dependency review, Dependabot, scheduled refresh, Pages deployment
- [x] Architecture, scoring, discovery, security, ADR and contributor documentation
