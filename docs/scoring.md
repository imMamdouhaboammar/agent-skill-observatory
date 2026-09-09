# Scoring model

The score is designed for comparison, not certification

Every catalog record exposes four component scores from 0 to 100

## Quality

Signals include open-spec validity, useful description length, instruction depth, repository tests or evals, and README evidence

## Security

Starts at 100 and applies documented deductions for static findings such as pipe-to-shell installation, recursive forced deletion, credential-path access, dynamic execution, world-writable permissions, and elevated privilege requests

No third-party code is executed to produce this score

## Maintenance

Recent pushes retain a higher score. Long inactivity reduces it. Archived repositories receive a strong penalty and the overall score is capped below 50 so old popularity cannot make an archived skill look actively maintained

## Adoption

Uses bounded logarithmic star and fork signals plus a historical 7-day star-velocity estimate when snapshots exist. This prevents raw star counts from dominating the entire ranking

## Overall

Current weights:

```text
35% quality
30% security
20% maintenance
15% adoption
```

A declared repository license adds a small bonus. Archived repositories are capped below 50 overall

The component scores and reasons are part of the record. Consumers should filter on the dimensions relevant to their own risk and use case instead of relying only on `overall`
