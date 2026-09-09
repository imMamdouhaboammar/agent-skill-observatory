# ADR 0002: Never execute third-party skills during indexing

Status: Accepted

## Context

Agent Skills may bundle executable scripts and may instruct an agent to perform network, filesystem, credential, or privileged operations

## Decision

Indexing and scoring are static only. The product will not execute third-party scripts to test them inside the primary crawler

## Consequences

The safety score is intentionally limited and must not be described as certification. Future dynamic evaluation, if added, must run in an isolated disposable sandbox as a separate trust domain and cannot weaken this default
