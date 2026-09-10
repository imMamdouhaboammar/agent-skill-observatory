# Scoring Model

<!-- Copyright (c) 2026 Mamdouh Aboammar. Licensed under Apache-2.0. -->

The score is designed for comparison, not certification.

Every catalog record exposes four component scores from 0 to 100.

## Quality (35%)

Signals include open-spec validity, useful description length, instruction depth,
repository tests or evals, and README evidence.

| Evidence | Points |
|---|---|
| Spec-valid manifest | +20 |
| Description ≥ 50 chars | +10 |
| Instruction body ≥ 200 chars | +10 |
| Tests or evals directory present | +15 |
| README ≥ 300 chars | +10 |
| Referenced resources exist | +10 |
| Examples or workflows present | +5 |

## Security (30%)

Starts at 100 and applies documented deductions for static findings.
No third-party code is executed to produce this score.

| Pattern | Deduction |
|---|---|
| `curl … \| bash` (pipe-to-shell) | −40 |
| `rm -rf` (recursive deletion) | −30 |
| Hardcoded credential / key path | −35 |
| `eval` / `exec` (dynamic execution) | −25 |
| `chmod 777` (world-writable) | −20 |
| `sudo` escalation | −15 |

A **high** security score means no high-impact static patterns were detected.
It is **not** a sandbox execution result and is **not** a safety guarantee.

## Maintenance (20%)

Recent pushes retain a higher score. Long inactivity reduces it.
Archived repositories receive a strong penalty and the overall score is capped below 50
so old popularity cannot make an archived skill appear actively maintained.

| Age since last push | Score band |
|---|---|
| < 30 days | 80–100 |
| 30–90 days | 60–80 |
| 90–365 days | 40–60 |
| > 365 days | 0–40 |
| Archived | capped < 50 overall |

## Adoption (15%)

Uses bounded logarithmic star and fork signals plus a historical 7-day star-velocity estimate
when snapshots exist. This prevents raw star counts from dominating the entire ranking.

```python
star_score  = min(log1p(stars) / log1p(1000), 1.0) * 60
fork_score  = min(log1p(forks) / log1p(200),  1.0) * 20
vel_score   = min(star_velocity / 10.0, 1.0) * 20   # velocity = Δstars/7 days
adoption    = star_score + fork_score + vel_score    # 0–100
```

## Overall

```text
overall = 0.35 × quality + 0.30 × security + 0.20 × maintenance + 0.15 × adoption
if archived: overall = min(overall, 49.9)
if license present: overall = min(overall + 2, 100)
```

A declared repository license adds a small bonus.
Archived repositories are capped below 50 overall.

The component scores and reasons are part of the record.
Consumers should filter on the dimensions relevant to their own risk and use case
instead of relying only on `overall`.
