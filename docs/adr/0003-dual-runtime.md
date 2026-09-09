# ADR 0003: Support service and GitHub-native static modes

Status: Accepted

## Context

A useful public catalog should be easy to run without paid infrastructure while still supporting a database-backed product deployment

## Decision

The same core package powers a FastAPI service backed by SQLite or PostgreSQL and a GitHub Actions workflow that exports a static JSON/CSV catalog for GitHub Pages

## Consequences

The UI must work against either the live API or static catalog files. Domain logic stays outside the web layer so both modes produce the same evidence model
