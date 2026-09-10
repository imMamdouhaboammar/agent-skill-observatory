# ADR 0004: Atomic Skill publication on main

Status: Accepted

## Context

The existing GitHub-native publisher regenerates aggregate catalog files and pushes them as one snapshot commit. That makes aggregate files act as both presentation and publication state, and a concurrent change to `main` can make the final push non-fast-forward after discovery and generation have already completed

The Observatory needs Git history to express semantic Skill changes independently while preserving human edits and allowing interrupted or concurrent runs to converge safely

## Decision

Publication truth moves to sharded per-Skill JSON records under `catalog/skills/**/record.json` on `main`

Each semantic Skill add, update, reindex, or confirmed removal is published as exactly one direct commit to `main`. A Skill event commit contains only that Skill's canonical record and the generated directory views affected by that event

`AWESOME.md` and `data/*` are materialized views derived from canonical published records. They are not used as the source of truth for Skill event detection and are updated separately from per-Skill commits

The runtime publisher uses GitHub Git Database objects. It reads the current branch ref and commit tree, renders one event against that state, creates blobs, a tree, and a commit, then attempts a fast-forward ref update. Ref updates never use force

If `main` advances before the ref update, the publisher reloads the current head, re-reads the affected publication state, recomputes the event outcome, rerenders affected files, and retries from the new head

Generated canonical Skill records, Skill pages, repository pages, and category pages are bot-owned. The root `README.md` is only partly bot-owned, so publication may replace only the content between the Awesome index markers

Retries do not rely on a separate durable event queue. Pending work is recomputed from observed semantic state minus canonical published state

## Consequences

Git history becomes meaningful at Skill granularity, and a run that stops after one Skill commit still leaves that published Skill internally consistent and browseable

Concurrent human or automation commits can advance `main` without being overwritten. A conflicting publication attempt is retried from the newer head using fast-forward-only ref movement

Aggregate outputs may lag behind the most recent Skill event until the batch materialization commit, but canonical per-Skill records remain authoritative and aggregates stay reproducible

Bootstrap publication uses the same event pipeline as normal scheduled publication. Operational batching limits work per run without combining semantic Skill events into larger commits

A corrupted canonical record is publication infrastructure failure and must fail closed rather than being silently skipped
