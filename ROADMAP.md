# Roadmap

## 0.2: Better evidence

- Track per-skill version changes instead of only current manifest state
- Add repository contributor and release signals with quota-aware caching
- Detect forks and generated mirrors separately from exact content duplicates
- Add richer client metadata parsing such as `agents/openai.yaml`
- Expose historical score and adoption timelines through API endpoints

## 0.3: Search and ranking

- PostgreSQL full-text search profile
- optional embeddings generated from safe metadata only
- saved filters and named ranking views
- category and client filters at API level
- explain-why-this-result responses

## 0.4: Evaluation

- isolated disposable sandbox runner as a separate service
- explicit network, filesystem, credential, and command policies
- reproducible eval fixtures
- resource budgets and timeouts
- signed evaluation reports linked to exact content fingerprints

Dynamic evaluation must never be added by weakening the primary crawler's no-execution rule

## 1.0

- stable catalog schema and versioned API
- zero-downtime migration policy for large PostgreSQL deployments
- public provenance and score methodology contract
- moderation and dispute workflow for false positives and provenance corrections
- signed release artifacts and SBOM
