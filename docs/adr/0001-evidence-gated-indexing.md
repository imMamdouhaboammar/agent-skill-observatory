# ADR 0001: Evidence-gated indexing

Status: Accepted

## Context

GitHub search for repositories named around skills produces substantial unrelated noise and cannot establish that a repository contains an Agent Skill

## Decision

Search results are candidates only. A catalog record requires a fetched manifest path from the repository tree. The record stores source provenance and validation results

## Consequences

Discovery can remain broad without corrupting catalog quality. Refreshes require more GitHub API calls than a name-only tracker, so inspection is bounded and errors are isolated per repository
